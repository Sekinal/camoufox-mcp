"""
Website analysis tools for Camoufox MCP Server.

NEW tools for analyzing websites to determine optimal scraping strategies:
- detect_antibot_protection: Identify Cloudflare, Akamai, PerimeterX, etc.
- analyze_page_structure: DOM complexity, shadow DOMs, iframes, frameworks
- analyze_network_patterns: API endpoints, GraphQL, WebSocket detection
- test_selector: Validate CSS/XPath selectors
- analyze_resource_loading: Script timing, blocking resources
- export_har: Export network log in HAR format
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.models import (
    AntiBotDetectionResult,
    NetworkPatternAnalysis,
    PageStructureAnalysis,
    SelectorTestResult,
)
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_selector

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register website analysis tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def detect_antibot_protection() -> str:
        """
        Analyze the current page for anti-bot protection systems.

        Detects:
        - Cloudflare (cf-ray header, challenge pages, cookies)
        - Akamai Bot Manager (_abck cookie, akamai scripts)
        - PerimeterX (_px cookies, challenge scripts)
        - DataDome (datadome cookie)
        - reCAPTCHA and hCaptcha

        Returns:
            JSON object with detection results and indicators
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        result = AntiBotDetectionResult()

        try:
            # Get cookies
            cookies = await session.page.context.cookies()
            cookie_names = {c["name"] for c in cookies}

            # Get response headers from network log
            response_headers = {}
            for entry in reversed(session.network_log):
                if entry.resource_type == "document" and entry.response_headers:
                    response_headers = entry.response_headers
                    break

            # Check for Cloudflare
            cf_indicators = []
            if "cf-ray" in response_headers or "CF-RAY" in response_headers:
                cf_indicators.append("cf-ray header present")
            if "__cf_bm" in cookie_names:
                cf_indicators.append("__cf_bm cookie")
            if "cf_clearance" in cookie_names:
                cf_indicators.append("cf_clearance cookie (challenge passed)")

            # Check page content for Cloudflare challenge
            cf_challenge = await session.page.evaluate("""() => {
                const title = document.title.toLowerCase();
                const hasChallenge = title.includes('just a moment') ||
                                   title.includes('checking your browser') ||
                                   document.querySelector('#cf-wrapper') !== null ||
                                   document.querySelector('.cf-browser-verification') !== null;
                return hasChallenge;
            }""")
            if cf_challenge:
                cf_indicators.append("Cloudflare challenge page detected")

            result.cloudflare_detected = len(cf_indicators) > 0
            result.cloudflare_indicators = cf_indicators

            # Check for Akamai Bot Manager
            akamai_indicators = []
            if "_abck" in cookie_names:
                akamai_indicators.append("_abck cookie (Akamai Bot Manager)")
            if "bm_sz" in cookie_names:
                akamai_indicators.append("bm_sz cookie")

            akamai_scripts = await session.page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script[src]'));
                return scripts.some(s => s.src.includes('akamai') || s.src.includes('_sec'));
            }""")
            if akamai_scripts:
                akamai_indicators.append("Akamai script detected")

            result.akamai_detected = len(akamai_indicators) > 0
            result.akamai_indicators = akamai_indicators

            # Check for PerimeterX
            px_indicators = []
            px_cookies = [c for c in cookie_names if c.startswith("_px")]
            if px_cookies:
                px_indicators.append(f"PerimeterX cookies: {', '.join(px_cookies)}")

            px_scripts = await session.page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script'));
                return scripts.some(s =>
                    (s.src && s.src.includes('perimeterx')) ||
                    (s.textContent && s.textContent.includes('_pxAppId'))
                );
            }""")
            if px_scripts:
                px_indicators.append("PerimeterX script detected")

            result.perimeterx_detected = len(px_indicators) > 0
            result.perimeterx_indicators = px_indicators

            # Check for DataDome
            dd_indicators = []
            if "datadome" in cookie_names:
                dd_indicators.append("datadome cookie")

            dd_scripts = await session.page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script[src]'));
                return scripts.some(s => s.src.includes('datadome'));
            }""")
            if dd_scripts:
                dd_indicators.append("DataDome script detected")

            result.datadome_detected = len(dd_indicators) > 0
            result.datadome_indicators = dd_indicators

            # Check for CAPTCHA
            captcha_info = await session.page.evaluate("""() => {
                const result = {detected: false, type: null, indicators: []};

                // reCAPTCHA v2/v3
                if (document.querySelector('.g-recaptcha') ||
                    document.querySelector('[data-sitekey]') ||
                    typeof grecaptcha !== 'undefined') {
                    result.detected = true;
                    result.type = 'reCAPTCHA';
                    result.indicators.push('reCAPTCHA element found');
                }

                // hCaptcha
                if (document.querySelector('.h-captcha') ||
                    document.querySelector('[data-hcaptcha-sitekey]')) {
                    result.detected = true;
                    result.type = 'hCaptcha';
                    result.indicators.push('hCaptcha element found');
                }

                // Turnstile
                if (document.querySelector('.cf-turnstile')) {
                    result.detected = true;
                    result.type = 'Cloudflare Turnstile';
                    result.indicators.push('Turnstile element found');
                }

                return result;
            }""")

            result.captcha_detected = captcha_info["detected"]
            result.captcha_type = captcha_info["type"]
            result.captcha_indicators = captcha_info["indicators"]

            # Check for other protections
            other = []

            # Imperva/Incapsula
            if "incap_ses" in str(cookie_names) or "visid_incap" in str(cookie_names):
                other.append("Imperva/Incapsula detected (incap cookies)")

            # Distil Networks
            if any("distil" in c.lower() for c in cookie_names):
                other.append("Distil Networks detected")

            # Shape Security
            shape_scripts = await session.page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script'));
                return scripts.some(s => s.textContent && s.textContent.includes('_cf_chl'));
            }""")

            result.other_protections = other

            return json.dumps(result.to_dict(), indent=2)

        except Exception as e:
            return f"Error detecting anti-bot protection: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def analyze_page_structure() -> str:
        """
        Analyze the DOM structure of the current page.

        Provides insights into:
        - Total element count and breakdown by tag
        - Shadow DOM usage
        - iframe count and nesting
        - Framework detection (React, Vue, Angular)
        - Dynamic content markers
        - Form and input analysis

        Returns:
            JSON object with page structure analysis
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            analysis = await session.page.evaluate("""() => {
                const result = {
                    total_elements: 0,
                    element_counts: {},
                    shadow_dom_count: 0,
                    iframe_count: 0,
                    iframe_nesting_depth: 0,
                    form_count: 0,
                    input_count: 0,
                    link_count: 0,
                    script_count: 0,
                    framework_detected: null,
                    lazy_load_indicators: [],
                    dynamic_content_markers: []
                };

                // Count elements by tag
                const allElements = document.querySelectorAll('*');
                result.total_elements = allElements.length;

                const tagCounts = {};
                allElements.forEach(el => {
                    const tag = el.tagName.toLowerCase();
                    tagCounts[tag] = (tagCounts[tag] || 0) + 1;

                    // Check for shadow DOM
                    if (el.shadowRoot) {
                        result.shadow_dom_count++;
                    }
                });
                result.element_counts = tagCounts;

                // Specific counts
                result.iframe_count = document.querySelectorAll('iframe').length;
                result.form_count = document.querySelectorAll('form').length;
                result.input_count = document.querySelectorAll('input, textarea, select').length;
                result.link_count = document.querySelectorAll('a').length;
                result.script_count = document.querySelectorAll('script').length;

                // Calculate iframe nesting depth
                function getMaxIframeDepth(doc, depth = 0) {
                    const iframes = doc.querySelectorAll('iframe');
                    let maxDepth = depth;
                    iframes.forEach(iframe => {
                        try {
                            if (iframe.contentDocument) {
                                maxDepth = Math.max(maxDepth, getMaxIframeDepth(iframe.contentDocument, depth + 1));
                            }
                        } catch (e) {
                            // Cross-origin iframe
                            maxDepth = Math.max(maxDepth, depth + 1);
                        }
                    });
                    return maxDepth;
                }
                result.iframe_nesting_depth = getMaxIframeDepth(document);

                // Framework detection
                if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__ || document.querySelector('[data-reactroot]')) {
                    result.framework_detected = 'React';
                } else if (window.__VUE__ || document.querySelector('[data-v-]')) {
                    result.framework_detected = 'Vue';
                } else if (window.ng || document.querySelector('[ng-app], [data-ng-app], .ng-scope')) {
                    result.framework_detected = 'Angular';
                } else if (window.Svelte || document.querySelector('[class*="svelte-"]')) {
                    result.framework_detected = 'Svelte';
                } else if (window.Ember) {
                    result.framework_detected = 'Ember';
                } else if (document.querySelector('[data-turbo], [data-turbolinks]')) {
                    result.framework_detected = 'Turbo/Hotwire';
                }

                // Lazy loading indicators
                const lazyIndicators = [];
                if (document.querySelector('[loading="lazy"]')) {
                    lazyIndicators.push('Native lazy loading (loading="lazy")');
                }
                if (document.querySelector('[data-src], [data-lazy]')) {
                    lazyIndicators.push('Data attribute lazy loading');
                }
                if (document.querySelector('.lazyload, .lazy')) {
                    lazyIndicators.push('Lazy loading CSS classes');
                }
                if (window.IntersectionObserver && document.querySelector('[data-observe]')) {
                    lazyIndicators.push('IntersectionObserver lazy loading');
                }
                result.lazy_load_indicators = lazyIndicators;

                // Dynamic content markers
                const dynamicMarkers = [];
                if (document.querySelector('[data-testid], [data-test]')) {
                    dynamicMarkers.push('Test IDs present (good for scraping)');
                }
                if (document.querySelectorAll('[id*="react"], [class*="react"]').length > 5) {
                    dynamicMarkers.push('React-generated IDs/classes');
                }
                if (document.querySelectorAll('[class*="css-"], [class*="sc-"]').length > 5) {
                    dynamicMarkers.push('CSS-in-JS (styled-components/emotion)');
                }
                if (document.querySelector('[data-hydrate], [data-ssr]')) {
                    dynamicMarkers.push('Server-side rendering markers');
                }
                result.dynamic_content_markers = dynamicMarkers;

                return result;
            }""")

            return json.dumps(analysis, indent=2)

        except Exception as e:
            return f"Error analyzing page structure: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def analyze_network_patterns() -> str:
        """
        Analyze captured network requests to identify API patterns.

        Detects:
        - REST API endpoints
        - GraphQL endpoints
        - WebSocket connections
        - Authentication patterns (tokens, cookies)
        - Third-party resources and CDNs

        Returns:
            JSON object with network pattern analysis
        """
        session = get_session()
        config = get_config()

        if not session.network_log:
            return json.dumps({
                "error": "No network requests captured. Navigate to a page first.",
                "tip": "Use goto() to load a page, then call this tool again."
            }, indent=2)

        result = NetworkPatternAnalysis()

        api_patterns = []
        graphql_endpoints = set()
        websocket_urls = set()
        auth_patterns = []
        domains = {}
        resource_counts = {}

        for entry in session.network_log:
            url = entry.url
            parsed = urlparse(url)
            domain = parsed.netloc

            # Count domains
            domains[domain] = domains.get(domain, 0) + 1

            # Count resource types
            rtype = entry.resource_type or "other"
            resource_counts[rtype] = resource_counts.get(rtype, 0) + 1

            # Detect API endpoints
            if entry.resource_type in ("fetch", "xhr"):
                api_info = {
                    "url": url,
                    "method": entry.method,
                    "status": entry.status,
                }

                # Check for common API patterns
                if "/api/" in url or "/v1/" in url or "/v2/" in url or "/graphql" in url:
                    api_info["pattern"] = "API endpoint"

                # Check for JSON responses
                content_type = entry.response_headers.get("content-type", "")
                if "application/json" in content_type:
                    api_info["response_type"] = "JSON"

                api_patterns.append(api_info)

            # Detect GraphQL
            if "/graphql" in url.lower() or entry.method == "POST":
                if entry.request_body and ("query" in str(entry.request_body) or "mutation" in str(entry.request_body)):
                    graphql_endpoints.add(url)

            # Detect WebSocket
            if url.startswith("wss://") or url.startswith("ws://"):
                websocket_urls.add(url)

            # Detect authentication patterns
            auth_headers = ["authorization", "x-auth-token", "x-api-key", "bearer"]
            for header in entry.request_headers:
                if any(auth in header.lower() for auth in auth_headers):
                    auth_patterns.append(f"Auth header: {header}")

        # Categorize domains
        cdn_patterns = ["cdn", "cloudfront", "akamai", "fastly", "cloudflare", "jsdelivr", "unpkg"]
        third_party = []
        cdns = []

        page_domain = ""
        if session.page:
            try:
                page_domain = urlparse(session.page.url).netloc
            except Exception:
                pass

        for domain, count in domains.items():
            if domain == page_domain:
                continue
            if any(cdn in domain.lower() for cdn in cdn_patterns):
                cdns.append(domain)
            else:
                third_party.append(domain)

        result.api_endpoints = api_patterns[:50]  # Limit to 50
        result.graphql_endpoints = list(graphql_endpoints)
        result.websocket_urls = list(websocket_urls)
        result.authentication_patterns = list(set(auth_patterns))
        result.third_party_domains = third_party
        result.cdn_domains = cdns
        result.resource_stats = resource_counts

        return json.dumps(result.to_dict(), indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def test_selector(
        selector: str,
        max_samples: int = 5,
    ) -> str:
        """
        Test a CSS or XPath selector and get detailed results.

        Validates the selector, counts matches, and provides:
        - Sample matched elements
        - Uniqueness assessment
        - Fragility warnings (e.g., auto-generated IDs)
        - Alternative selector suggestions

        Args:
            selector: CSS selector or XPath (starting with //)
            max_samples: Maximum number of sample elements to return

        Returns:
            JSON object with selector test results
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Validate selector
        valid, error = safe_validate(validate_selector, selector)
        if not valid:
            return json.dumps({
                "success": False,
                "error": f"Invalid selector: {error}",
            }, indent=2)

        try:
            # Determine selector type
            is_xpath = selector.startswith("//") or selector.startswith("(//")
            selector_type = "xpath" if is_xpath else "css"

            # Find elements
            if is_xpath:
                elements = await session.page.locator(f"xpath={selector}").all()
            else:
                elements = await session.page.locator(selector).all()

            match_count = len(elements)

            # Get sample elements
            samples = []
            for i, el in enumerate(elements[:max_samples]):
                try:
                    info = await el.evaluate("""el => ({
                        tag: el.tagName.toLowerCase(),
                        id: el.id,
                        className: el.className,
                        text: el.innerText?.substring(0, 100),
                        attributes: Array.from(el.attributes).slice(0, 10).map(a => ({
                            name: a.name,
                            value: a.value.substring(0, 50)
                        }))
                    })""")
                    samples.append(info)
                except Exception:
                    pass

            # Analyze for warnings
            warnings = []
            suggestions = []

            # Check for fragile patterns
            if re.search(r"[a-f0-9]{8,}", selector):
                warnings.append("Selector contains hash-like string (may be auto-generated)")

            if re.search(r"\d{4,}", selector):
                warnings.append("Selector contains long number sequence (may be auto-generated)")

            if "css-" in selector or "sc-" in selector:
                warnings.append("Selector uses CSS-in-JS class names (may change between builds)")

            if selector.count(" > ") > 3:
                warnings.append("Deep nesting (>3 levels) - may break with DOM changes")

            # Generate suggestions
            if match_count == 0:
                suggestions.append("No matches - check spelling and element existence")
                suggestions.append("Try a more general selector first, then narrow down")
            elif match_count > 1:
                suggestions.append(f"Found {match_count} matches - add more specificity for unique match")
                if samples and samples[0].get("id"):
                    suggestions.append(f"Try using ID: #{samples[0]['id']}")

            # Check if unique selectors exist
            if samples:
                sample = samples[0]
                if sample.get("id"):
                    suggestions.append(f"More stable alternative: #{sample['id']}")

                # Look for data-testid
                for attr in sample.get("attributes", []):
                    if attr["name"] in ("data-testid", "data-test", "data-cy"):
                        suggestions.append(f"Test ID available: [{attr['name']}=\"{attr['value']}\"]")

            result = SelectorTestResult(
                selector=selector,
                selector_type=selector_type,
                match_count=match_count,
                sample_elements=samples,
                is_unique=match_count == 1,
                warnings=warnings,
                suggestions=suggestions,
            )

            return json.dumps(result.to_dict(), indent=2)

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "selector": selector,
            }, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def analyze_resource_loading() -> str:
        """
        Analyze resource loading patterns and timing.

        Provides insights into:
        - Script loading order and blocking behavior
        - Render-blocking resources
        - Resource sizes and types
        - Loading timeline

        Returns:
            JSON object with resource loading analysis
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            # Get performance timing from browser
            timing_data = await session.page.evaluate("""() => {
                const perf = window.performance;
                const timing = perf.timing;
                const entries = perf.getEntriesByType('resource');

                // Basic timing
                const navTiming = {
                    dns_lookup_ms: timing.domainLookupEnd - timing.domainLookupStart,
                    tcp_connect_ms: timing.connectEnd - timing.connectStart,
                    ttfb_ms: timing.responseStart - timing.requestStart,
                    dom_interactive_ms: timing.domInteractive - timing.navigationStart,
                    dom_complete_ms: timing.domComplete - timing.navigationStart,
                    load_complete_ms: timing.loadEventEnd - timing.navigationStart,
                };

                // Resource entries
                const resources = entries.map(e => ({
                    name: e.name,
                    type: e.initiatorType,
                    duration_ms: Math.round(e.duration),
                    size: e.transferSize || 0,
                    start_time_ms: Math.round(e.startTime),
                    render_blocking: e.renderBlockingStatus || 'unknown'
                })).sort((a, b) => a.start_time_ms - b.start_time_ms);

                // Group by type
                const byType = {};
                resources.forEach(r => {
                    if (!byType[r.type]) {
                        byType[r.type] = {count: 0, total_size: 0, total_duration: 0};
                    }
                    byType[r.type].count++;
                    byType[r.type].total_size += r.size;
                    byType[r.type].total_duration += r.duration_ms;
                });

                // Find render-blocking resources
                const blocking = resources.filter(r =>
                    r.render_blocking === 'blocking' ||
                    (r.type === 'script' && r.start_time_ms < navTiming.dom_interactive_ms)
                );

                // Find slow resources
                const slow = resources.filter(r => r.duration_ms > 500)
                    .sort((a, b) => b.duration_ms - a.duration_ms)
                    .slice(0, 10);

                return {
                    timing: navTiming,
                    resource_summary: byType,
                    render_blocking: blocking.slice(0, 10),
                    slowest_resources: slow,
                    total_resources: resources.length,
                    total_transfer_size: resources.reduce((sum, r) => sum + r.size, 0)
                };
            }""")

            return json.dumps(timing_data, indent=2)

        except Exception as e:
            return f"Error analyzing resource loading: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def export_har() -> str:
        """
        Export the network log in HAR (HTTP Archive) format.

        HAR is a standard format for recording HTTP transactions.
        Can be imported into browser dev tools or analysis tools.

        Returns:
            JSON string in HAR format
        """
        session = get_session()

        if not session.network_log:
            return json.dumps({
                "error": "No network requests captured.",
                "tip": "Navigate to pages to capture requests, then export."
            }, indent=2)

        # Build HAR structure
        har = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "Camoufox MCP Server",
                    "version": "0.2.0"
                },
                "entries": []
            }
        }

        for entry in session.network_log:
            har_entry = {
                "startedDateTime": entry.timestamp.isoformat() if entry.timestamp else datetime.now(timezone.utc).isoformat(),
                "time": entry.duration_ms or 0,
                "request": {
                    "method": entry.method,
                    "url": entry.url,
                    "httpVersion": "HTTP/1.1",
                    "headers": [{"name": k, "value": v} for k, v in entry.request_headers.items()],
                    "queryString": [],
                    "cookies": [],
                    "headersSize": -1,
                    "bodySize": len(entry.request_body) if entry.request_body else 0,
                },
                "response": {
                    "status": entry.status or 0,
                    "statusText": "",
                    "httpVersion": "HTTP/1.1",
                    "headers": [{"name": k, "value": v} for k, v in entry.response_headers.items()],
                    "cookies": [],
                    "content": {
                        "size": len(entry.response_body) if entry.response_body else 0,
                        "mimeType": entry.response_headers.get("content-type", ""),
                        "text": entry.response_body if entry.response_body else "",
                    },
                    "redirectURL": "",
                    "headersSize": -1,
                    "bodySize": len(entry.response_body) if entry.response_body else 0,
                },
                "cache": {},
                "timings": entry.timing if entry.timing else {
                    "send": -1,
                    "wait": -1,
                    "receive": -1,
                },
                "serverIPAddress": "",
                "connection": "",
            }

            # Add request body if present
            if entry.request_body:
                har_entry["request"]["postData"] = {
                    "mimeType": entry.request_headers.get("content-type", ""),
                    "text": entry.request_body,
                }

            har["log"]["entries"].append(har_entry)

        return json.dumps(har, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def find_data_sources() -> str:
        """
        Identify potential data sources on the current page.

        Looks for:
        - JSON embedded in script tags
        - Data attributes with structured data
        - Meta tags with data
        - Microdata/JSON-LD structured data

        Returns:
            JSON object listing potential data sources
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            data_sources = await session.page.evaluate("""() => {
                const sources = {
                    json_ld: [],
                    inline_json: [],
                    data_attributes: [],
                    meta_data: [],
                    next_data: null,
                    nuxt_data: null,
                };

                // Find JSON-LD structured data
                document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
                    try {
                        const data = JSON.parse(script.textContent);
                        sources.json_ld.push({
                            type: data['@type'] || 'unknown',
                            preview: JSON.stringify(data).substring(0, 200)
                        });
                    } catch (e) {}
                });

                // Find inline JSON in scripts (common patterns)
                document.querySelectorAll('script:not([src])').forEach(script => {
                    const text = script.textContent;

                    // Look for window.__DATA__ patterns (use RegExp to avoid Python escape warnings)
                    const patterns = [
                        new RegExp('window\\.__[A-Z_]+__\\s*=\\s*(\\{[\\s\\S]*?\\});'),
                        new RegExp('window\\.[a-zA-Z_]+\\s*=\\s*(\\{[\\s\\S]*?\\});'),
                        new RegExp('"props":\\s*\\{[\\s\\S]*?\\}')
                    ];

                    patterns.forEach(pattern => {
                        const match = text.match(pattern);
                        if (match) {
                            sources.inline_json.push({
                                preview: match[0].substring(0, 200),
                                full_length: match[0].length
                            });
                        }
                    });
                });

                // Check for Next.js data
                const nextData = document.querySelector('#__NEXT_DATA__');
                if (nextData) {
                    try {
                        const data = JSON.parse(nextData.textContent);
                        sources.next_data = {
                            page: data.page,
                            has_props: !!data.props,
                            preview: JSON.stringify(data.props?.pageProps || {}).substring(0, 200)
                        };
                    } catch (e) {}
                }

                // Check for Nuxt data
                const nuxtData = document.querySelector('#__NUXT_DATA__') ||
                                window.__NUXT__;
                if (nuxtData) {
                    sources.nuxt_data = {
                        detected: true,
                        type: typeof nuxtData
                    };
                }

                // Find elements with data attributes containing JSON-like content
                document.querySelectorAll('[data-props], [data-state], [data-initial]').forEach(el => {
                    const attrs = ['data-props', 'data-state', 'data-initial'];
                    attrs.forEach(attr => {
                        const value = el.getAttribute(attr);
                        if (value && value.startsWith('{')) {
                            sources.data_attributes.push({
                                attribute: attr,
                                selector: el.tagName.toLowerCase() +
                                    (el.id ? '#' + el.id : '') +
                                    (el.className ? '.' + el.className.split(' ')[0] : ''),
                                preview: value.substring(0, 200)
                            });
                        }
                    });
                });

                // Get relevant meta tags
                document.querySelectorAll('meta[property], meta[name]').forEach(meta => {
                    const prop = meta.getAttribute('property') || meta.getAttribute('name');
                    const content = meta.getAttribute('content');
                    if (content && (
                        prop.startsWith('og:') ||
                        prop.startsWith('twitter:') ||
                        prop.includes('price') ||
                        prop.includes('product')
                    )) {
                        sources.meta_data.push({property: prop, content: content});
                    }
                });

                return sources;
            }""")

            return json.dumps(data_sources, indent=2)

        except Exception as e:
            return f"Error finding data sources: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def monitor_fingerprinting(duration_ms: int = 5000) -> str:
        """
        Hook browser APIs to monitor what fingerprinting data scripts are collecting.

        Intercepts calls to commonly fingerprinted APIs and logs what's accessed.
        Run this, then trigger page actions or wait for scripts to execute.

        Args:
            duration_ms: How long to monitor (default 5 seconds)

        Returns:
            JSON object with all intercepted fingerprinting attempts
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            # Inject monitoring hooks and collect for duration
            result = await session.page.evaluate("""(duration) => {
                return new Promise((resolve) => {
                    const log = {
                        canvas: [],
                        webgl: [],
                        audio: [],
                        navigator: [],
                        screen: [],
                        timing: [],
                        fonts: [],
                        plugins: [],
                        other: []
                    };

                    // Hook canvas fingerprinting
                    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                    HTMLCanvasElement.prototype.toDataURL = function(...args) {
                        log.canvas.push({method: 'toDataURL', args: args.map(String)});
                        return originalToDataURL.apply(this, args);
                    };

                    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                    CanvasRenderingContext2D.prototype.getImageData = function(...args) {
                        log.canvas.push({method: 'getImageData', args: args.map(String)});
                        return originalGetImageData.apply(this, args);
                    };

                    // Hook WebGL fingerprinting
                    const hookWebGL = (proto, name) => {
                        const original = proto.getParameter;
                        if (original) {
                            proto.getParameter = function(param) {
                                const paramNames = {
                                    7937: 'VENDOR', 7936: 'RENDERER', 37445: 'UNMASKED_VENDOR',
                                    37446: 'UNMASKED_RENDERER', 7938: 'VERSION'
                                };
                                if (paramNames[param]) {
                                    log.webgl.push({method: 'getParameter', param: paramNames[param] || param});
                                }
                                return original.call(this, param);
                            };
                        }
                    };
                    if (window.WebGLRenderingContext) hookWebGL(WebGLRenderingContext.prototype, 'webgl');
                    if (window.WebGL2RenderingContext) hookWebGL(WebGL2RenderingContext.prototype, 'webgl2');

                    // Hook AudioContext fingerprinting
                    if (window.AudioContext || window.webkitAudioContext) {
                        const AC = window.AudioContext || window.webkitAudioContext;
                        const origCreateOscillator = AC.prototype.createOscillator;
                        AC.prototype.createOscillator = function() {
                            log.audio.push({method: 'createOscillator'});
                            return origCreateOscillator.apply(this);
                        };
                    }

                    // Hook navigator property access
                    const navProps = ['userAgent', 'platform', 'language', 'languages',
                                     'hardwareConcurrency', 'deviceMemory', 'webdriver',
                                     'plugins', 'mimeTypes', 'cookieEnabled', 'doNotTrack'];
                    navProps.forEach(prop => {
                        try {
                            const desc = Object.getOwnPropertyDescriptor(Navigator.prototype, prop) ||
                                        Object.getOwnPropertyDescriptor(navigator, prop);
                            if (desc && desc.get) {
                                const originalGet = desc.get;
                                Object.defineProperty(navigator, prop, {
                                    get: function() {
                                        log.navigator.push({property: prop});
                                        return originalGet.call(this);
                                    }
                                });
                            }
                        } catch(e) {}
                    });

                    // Hook screen properties
                    const screenProps = ['width', 'height', 'availWidth', 'availHeight',
                                        'colorDepth', 'pixelDepth'];
                    screenProps.forEach(prop => {
                        try {
                            const desc = Object.getOwnPropertyDescriptor(Screen.prototype, prop);
                            if (desc && desc.get) {
                                const originalGet = desc.get;
                                Object.defineProperty(screen, prop, {
                                    get: function() {
                                        log.screen.push({property: prop});
                                        return originalGet.call(this);
                                    }
                                });
                            }
                        } catch(e) {}
                    });

                    // Hook performance/timing
                    if (window.performance) {
                        const origNow = performance.now;
                        performance.now = function() {
                            log.timing.push({method: 'performance.now'});
                            return origNow.call(this);
                        };
                    }

                    // Hook font detection (common technique)
                    const origOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
                    if (origOffsetWidth) {
                        Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
                            get: function() {
                                const el = this;
                                if (el.style && el.style.fontFamily) {
                                    log.fonts.push({font: el.style.fontFamily});
                                }
                                return origOffsetWidth.get.call(this);
                            }
                        });
                    }

                    // Collect for specified duration
                    setTimeout(() => {
                        // Deduplicate and summarize
                        const summarize = (arr) => {
                            const counts = {};
                            arr.forEach(item => {
                                const key = JSON.stringify(item);
                                counts[key] = (counts[key] || 0) + 1;
                            });
                            return Object.entries(counts).map(([k, v]) => ({...JSON.parse(k), count: v}));
                        };

                        resolve({
                            canvas: summarize(log.canvas),
                            webgl: summarize(log.webgl),
                            audio: summarize(log.audio),
                            navigator: summarize(log.navigator),
                            screen: summarize(log.screen),
                            timing: log.timing.length > 0 ? {calls: log.timing.length} : null,
                            fonts: log.fonts.length > 0 ? {unique_fonts_probed: [...new Set(log.fonts.map(f => f.font))].length} : null
                        });
                    }, duration);
                });
            }""", duration_ms)

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error monitoring fingerprinting: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def snapshot_state(snapshot_id: str = "default") -> str:
        """
        Take a snapshot of current page state (cookies, storage, DOM info).

        Use this before an action, then use diff_state after to see what changed.

        Args:
            snapshot_id: Identifier for this snapshot (for multiple snapshots)

        Returns:
            Confirmation message
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if not hasattr(session, "_snapshots"):
            session._snapshots = {}

        try:
            cookies = await session.page.context.cookies()
            storage = await session.page.evaluate("""() => ({
                localStorage: Object.fromEntries(Object.entries(localStorage)),
                sessionStorage: Object.fromEntries(Object.entries(sessionStorage))
            })""")
            dom_info = await session.page.evaluate("""() => ({
                url: location.href,
                title: document.title,
                elementCount: document.querySelectorAll('*').length,
                bodyHash: document.body ? document.body.innerText.length : 0
            })""")
            network_count = len(session.network_log)

            session._snapshots[snapshot_id] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cookies": {c["name"]: c["value"] for c in cookies},
                "localStorage": storage["localStorage"],
                "sessionStorage": storage["sessionStorage"],
                "dom": dom_info,
                "networkLogCount": network_count
            }

            return f"Snapshot '{snapshot_id}' saved. Use diff_state('{snapshot_id}') after your action."

        except Exception as e:
            return f"Error taking snapshot: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def diff_state(snapshot_id: str = "default") -> str:
        """
        Compare current state with a previous snapshot.

        Shows what cookies, storage, DOM, and network activity changed.

        Args:
            snapshot_id: Which snapshot to compare against

        Returns:
            JSON object showing all changes
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if not hasattr(session, "_snapshots") or snapshot_id not in session._snapshots:
            return f"Error: No snapshot '{snapshot_id}' found. Use snapshot_state first."

        try:
            before = session._snapshots[snapshot_id]

            # Get current state
            cookies = await session.page.context.cookies()
            storage = await session.page.evaluate("""() => ({
                localStorage: Object.fromEntries(Object.entries(localStorage)),
                sessionStorage: Object.fromEntries(Object.entries(sessionStorage))
            })""")
            dom_info = await session.page.evaluate("""() => ({
                url: location.href,
                title: document.title,
                elementCount: document.querySelectorAll('*').length,
                bodyHash: document.body ? document.body.innerText.length : 0
            })""")
            network_count = len(session.network_log)

            current_cookies = {c["name"]: c["value"] for c in cookies}

            # Compute diffs
            def dict_diff(before_dict, after_dict):
                added = {k: v for k, v in after_dict.items() if k not in before_dict}
                removed = {k: v for k, v in before_dict.items() if k not in after_dict}
                changed = {k: {"before": before_dict[k], "after": after_dict[k]}
                          for k in before_dict if k in after_dict and before_dict[k] != after_dict[k]}
                return {"added": added, "removed": removed, "changed": changed}

            diff = {
                "snapshot_id": snapshot_id,
                "time_elapsed": f"from {before['timestamp']}",
                "cookies": dict_diff(before["cookies"], current_cookies),
                "localStorage": dict_diff(before["localStorage"], storage["localStorage"]),
                "sessionStorage": dict_diff(before["sessionStorage"], storage["sessionStorage"]),
                "dom": {
                    "url_changed": before["dom"]["url"] != dom_info["url"],
                    "before_url": before["dom"]["url"] if before["dom"]["url"] != dom_info["url"] else None,
                    "after_url": dom_info["url"] if before["dom"]["url"] != dom_info["url"] else None,
                    "title_changed": before["dom"]["title"] != dom_info["title"],
                    "element_count_diff": dom_info["elementCount"] - before["dom"]["elementCount"],
                    "content_length_diff": dom_info["bodyHash"] - before["dom"]["bodyHash"]
                },
                "network": {
                    "new_requests": network_count - before["networkLogCount"]
                }
            }

            # Clean up empty diffs
            for key in ["cookies", "localStorage", "sessionStorage"]:
                if not any(diff[key].values()):
                    diff[key] = "no changes"

            return json.dumps(diff, indent=2)

        except Exception as e:
            return f"Error computing diff: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def inject_init_script(script: str, name: str = "custom") -> str:
        """
        Inject JavaScript that runs BEFORE any page scripts load.

        Use this to hook browser APIs before anti-bot scripts can detect them.
        Scripts persist across navigations until browser is closed.

        Example hooks:
        - Override navigator.webdriver to return undefined
        - Hook canvas.toDataURL to return fake fingerprints
        - Intercept fetch/XMLHttpRequest to log API calls
        - Mock window.Notification or other APIs

        Args:
            script: JavaScript code to inject (runs in page context)
            name: Identifier for this script (for tracking)

        Returns:
            Confirmation message
        """
        session = get_session()

        if not session.page:
            return "Error: No active page. Launch browser first."

        if not script.strip():
            return "Error: Script cannot be empty."

        try:
            # Track injected scripts on session
            if not hasattr(session, "_init_scripts"):
                session._init_scripts = []

            # Add the init script - runs before page load on all future navigations
            await session.page.context.add_init_script(script)

            session._init_scripts.append({
                "name": name,
                "length": len(script),
                "preview": script[:100] + "..." if len(script) > 100 else script
            })

            return json.dumps({
                "success": True,
                "message": f"Init script '{name}' injected. Will run before page scripts on next navigation.",
                "scripts_active": len(session._init_scripts),
                "note": "Navigate to a page to see the script execute."
            }, indent=2)

        except Exception as e:
            return f"Error injecting script: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def list_init_scripts() -> str:
        """
        List all init scripts currently injected.

        Returns:
            JSON array of injected scripts with names and previews
        """
        session = get_session()

        if not hasattr(session, "_init_scripts") or not session._init_scripts:
            return json.dumps({
                "scripts": [],
                "message": "No init scripts injected yet."
            }, indent=2)

        return json.dumps({
            "scripts": session._init_scripts,
            "total": len(session._init_scripts),
            "note": "Scripts run in order of injection before each page load."
        }, indent=2)
