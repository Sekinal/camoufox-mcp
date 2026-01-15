"""
Performance analysis tools for Camoufox MCP Server.

Provides performance metrics, timing analysis, and Core Web Vitals.

Tools: get_performance_metrics, get_navigation_timing, get_resource_timing,
       analyze_performance, get_memory_info, get_coverage
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register performance analysis tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_performance_metrics() -> str:
        """
        Get Chrome DevTools performance metrics.

        Returns metrics like:
        - JSHeapUsedSize, JSHeapTotalSize
        - Documents, Frames, Nodes
        - LayoutCount, RecalcStyleCount
        - ScriptDuration, TaskDuration

        Returns:
            JSON object with performance metrics
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            import json

            client = await session.page.context.new_cdp_session(session.page)

            # Enable performance domain
            await client.send("Performance.enable", {})

            # Get metrics
            result = await client.send("Performance.getMetrics", {})

            # Format metrics nicely
            metrics = {}
            for metric in result.get("metrics", []):
                name = metric["name"]
                value = metric["value"]
                metrics[name] = value

            # Categorize metrics
            categorized = {
                "memory": {
                    "js_heap_used_mb": round(metrics.get("JSHeapUsedSize", 0) / 1024 / 1024, 2),
                    "js_heap_total_mb": round(metrics.get("JSHeapTotalSize", 0) / 1024 / 1024, 2),
                },
                "dom": {
                    "documents": metrics.get("Documents", 0),
                    "frames": metrics.get("Frames", 0),
                    "nodes": metrics.get("Nodes", 0),
                    "layout_objects": metrics.get("LayoutObjects", 0),
                },
                "rendering": {
                    "layout_count": metrics.get("LayoutCount", 0),
                    "recalc_style_count": metrics.get("RecalcStyleCount", 0),
                    "layout_duration_ms": round(metrics.get("LayoutDuration", 0) * 1000, 2),
                    "recalc_style_duration_ms": round(metrics.get("RecalcStyleDuration", 0) * 1000, 2),
                },
                "script": {
                    "script_duration_ms": round(metrics.get("ScriptDuration", 0) * 1000, 2),
                    "task_duration_ms": round(metrics.get("TaskDuration", 0) * 1000, 2),
                },
                "raw": metrics,
            }

            return json.dumps(categorized, indent=2)

        except Exception as e:
            return f"Error getting performance metrics: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_navigation_timing() -> str:
        """
        Get navigation timing metrics (page load performance).

        Returns timing data including:
        - DNS lookup, TCP connection, TLS handshake
        - Request/response times
        - DOM parsing and loading times
        - Overall page load time

        Returns:
            JSON object with navigation timing breakdown
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            import json

            timing = await session.page.evaluate("""
                () => {
                    const timing = performance.timing;
                    const nav = performance.getEntriesByType('navigation')[0];

                    if (nav) {
                        return {
                            type: nav.type,
                            redirectCount: nav.redirectCount,

                            // DNS
                            dns_lookup_ms: nav.domainLookupEnd - nav.domainLookupStart,

                            // Connection
                            tcp_connect_ms: nav.connectEnd - nav.connectStart,
                            tls_handshake_ms: nav.secureConnectionStart > 0
                                ? nav.connectEnd - nav.secureConnectionStart : 0,

                            // Request/Response
                            request_ms: nav.responseStart - nav.requestStart,
                            response_ms: nav.responseEnd - nav.responseStart,
                            ttfb_ms: nav.responseStart - nav.fetchStart,

                            // Processing
                            dom_interactive_ms: nav.domInteractive - nav.responseEnd,
                            dom_content_loaded_ms: nav.domContentLoadedEventEnd - nav.fetchStart,
                            dom_complete_ms: nav.domComplete - nav.fetchStart,

                            // Full page load
                            load_event_ms: nav.loadEventEnd - nav.fetchStart,

                            // Transfer
                            transfer_size_kb: Math.round(nav.transferSize / 1024),
                            encoded_body_size_kb: Math.round(nav.encodedBodySize / 1024),
                            decoded_body_size_kb: Math.round(nav.decodedBodySize / 1024),
                        };
                    } else {
                        // Fallback to legacy timing API
                        const t = timing;
                        return {
                            dns_lookup_ms: t.domainLookupEnd - t.domainLookupStart,
                            tcp_connect_ms: t.connectEnd - t.connectStart,
                            request_ms: t.responseStart - t.requestStart,
                            response_ms: t.responseEnd - t.responseStart,
                            ttfb_ms: t.responseStart - t.navigationStart,
                            dom_interactive_ms: t.domInteractive - t.responseEnd,
                            dom_content_loaded_ms: t.domContentLoadedEventEnd - t.navigationStart,
                            dom_complete_ms: t.domComplete - t.navigationStart,
                            load_event_ms: t.loadEventEnd - t.navigationStart,
                        };
                    }
                }
            """)

            return json.dumps(timing, indent=2)

        except Exception as e:
            return f"Error getting navigation timing: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_resource_timing(
        resource_type: str | None = None,
        limit: int = 50,
    ) -> str:
        """
        Get resource timing data for page assets.

        Args:
            resource_type: Filter by type (script, stylesheet, img, font, fetch, xmlhttprequest)
            limit: Maximum number of resources to return (default: 50)

        Returns:
            JSON array of resource timing entries
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            import json

            resources = await session.page.evaluate(f"""
                () => {{
                    const entries = performance.getEntriesByType('resource');
                    let filtered = entries;

                    const resourceType = '{resource_type or ''}';
                    if (resourceType) {{
                        filtered = entries.filter(e => e.initiatorType === resourceType);
                    }}

                    return filtered.slice(0, {limit}).map(r => ({{
                        name: r.name.split('/').pop().substring(0, 50),
                        url: r.name.substring(0, 100),
                        type: r.initiatorType,
                        duration_ms: Math.round(r.duration),
                        transfer_size_kb: Math.round(r.transferSize / 1024),
                        dns_ms: Math.round(r.domainLookupEnd - r.domainLookupStart),
                        tcp_ms: Math.round(r.connectEnd - r.connectStart),
                        ttfb_ms: Math.round(r.responseStart - r.requestStart),
                        download_ms: Math.round(r.responseEnd - r.responseStart),
                        cached: r.transferSize === 0,
                    }}));
                }}
            """)

            # Add summary
            total_size = sum(r.get("transfer_size_kb", 0) for r in resources)
            total_duration = sum(r.get("duration_ms", 0) for r in resources)
            by_type = {}
            for r in resources:
                t = r.get("type", "other")
                by_type[t] = by_type.get(t, 0) + 1

            result = {
                "summary": {
                    "total_resources": len(resources),
                    "total_size_kb": total_size,
                    "total_duration_ms": total_duration,
                    "by_type": by_type,
                },
                "resources": resources,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting resource timing: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def analyze_performance() -> str:
        """
        Comprehensive performance analysis with insights and recommendations.

        Analyzes:
        - Core Web Vitals (LCP, FID, CLS approximations)
        - Navigation timing
        - Resource loading
        - JavaScript execution
        - Memory usage

        Returns:
            JSON object with performance analysis and recommendations
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            import json

            # Collect all performance data
            analysis = await session.page.evaluate("""
                () => {
                    const result = {
                        url: window.location.href,
                        timestamp: new Date().toISOString(),
                        metrics: {},
                        issues: [],
                        recommendations: [],
                    };

                    // Navigation timing
                    const nav = performance.getEntriesByType('navigation')[0];
                    if (nav) {
                        result.metrics.ttfb_ms = Math.round(nav.responseStart - nav.fetchStart);
                        result.metrics.dom_content_loaded_ms = Math.round(nav.domContentLoadedEventEnd - nav.fetchStart);
                        result.metrics.load_complete_ms = Math.round(nav.loadEventEnd - nav.fetchStart);
                        result.metrics.transfer_size_kb = Math.round(nav.transferSize / 1024);

                        // Check TTFB
                        if (result.metrics.ttfb_ms > 600) {
                            result.issues.push({
                                severity: 'high',
                                metric: 'TTFB',
                                value: result.metrics.ttfb_ms + 'ms',
                                threshold: '< 600ms',
                                message: 'Time to First Byte is too slow',
                            });
                            result.recommendations.push('Optimize server response time, consider CDN');
                        } else if (result.metrics.ttfb_ms > 200) {
                            result.issues.push({
                                severity: 'medium',
                                metric: 'TTFB',
                                value: result.metrics.ttfb_ms + 'ms',
                                threshold: '< 200ms ideal',
                                message: 'Time to First Byte could be improved',
                            });
                        }

                        // Check page load
                        if (result.metrics.load_complete_ms > 3000) {
                            result.issues.push({
                                severity: 'high',
                                metric: 'Page Load',
                                value: result.metrics.load_complete_ms + 'ms',
                                threshold: '< 3000ms',
                                message: 'Page load is too slow',
                            });
                        }
                    }

                    // Resource analysis
                    const resources = performance.getEntriesByType('resource');
                    result.metrics.resource_count = resources.length;
                    result.metrics.total_transfer_kb = Math.round(
                        resources.reduce((sum, r) => sum + (r.transferSize || 0), 0) / 1024
                    );

                    // Count by type
                    const byType = {};
                    resources.forEach(r => {
                        byType[r.initiatorType] = (byType[r.initiatorType] || 0) + 1;
                    });
                    result.metrics.resources_by_type = byType;

                    // Find slow resources
                    const slowResources = resources
                        .filter(r => r.duration > 500)
                        .map(r => ({
                            url: r.name.substring(0, 80),
                            duration_ms: Math.round(r.duration),
                            size_kb: Math.round(r.transferSize / 1024),
                        }))
                        .slice(0, 5);

                    if (slowResources.length > 0) {
                        result.metrics.slow_resources = slowResources;
                        result.issues.push({
                            severity: 'medium',
                            metric: 'Slow Resources',
                            value: slowResources.length + ' resources > 500ms',
                            message: 'Some resources are loading slowly',
                        });
                        result.recommendations.push('Optimize or lazy-load slow resources');
                    }

                    // Large resources
                    const largeResources = resources
                        .filter(r => r.transferSize > 100 * 1024)
                        .map(r => ({
                            url: r.name.substring(0, 80),
                            size_kb: Math.round(r.transferSize / 1024),
                            type: r.initiatorType,
                        }))
                        .slice(0, 5);

                    if (largeResources.length > 0) {
                        result.metrics.large_resources = largeResources;
                        result.issues.push({
                            severity: 'medium',
                            metric: 'Large Resources',
                            value: largeResources.length + ' resources > 100KB',
                            message: 'Some resources are too large',
                        });
                        result.recommendations.push('Compress images, minify JS/CSS');
                    }

                    // Check for too many requests
                    if (resources.length > 100) {
                        result.issues.push({
                            severity: 'high',
                            metric: 'Request Count',
                            value: resources.length,
                            threshold: '< 100',
                            message: 'Too many HTTP requests',
                        });
                        result.recommendations.push('Bundle resources, use HTTP/2');
                    }

                    // Render-blocking resources
                    const renderBlocking = resources.filter(r =>
                        (r.initiatorType === 'script' || r.initiatorType === 'css') &&
                        r.renderBlockingStatus === 'blocking'
                    );
                    if (renderBlocking.length > 0) {
                        result.metrics.render_blocking_count = renderBlocking.length;
                        result.issues.push({
                            severity: 'medium',
                            metric: 'Render Blocking',
                            value: renderBlocking.length + ' resources',
                            message: 'Render-blocking resources detected',
                        });
                        result.recommendations.push('Defer non-critical scripts, inline critical CSS');
                    }

                    // LCP approximation
                    const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
                    if (lcpEntries.length > 0) {
                        const lcp = lcpEntries[lcpEntries.length - 1];
                        result.metrics.lcp_ms = Math.round(lcp.startTime);

                        if (result.metrics.lcp_ms > 4000) {
                            result.issues.push({
                                severity: 'high',
                                metric: 'LCP',
                                value: result.metrics.lcp_ms + 'ms',
                                threshold: '< 2500ms good, < 4000ms needs improvement',
                                message: 'Largest Contentful Paint is poor',
                            });
                        } else if (result.metrics.lcp_ms > 2500) {
                            result.issues.push({
                                severity: 'medium',
                                metric: 'LCP',
                                value: result.metrics.lcp_ms + 'ms',
                                threshold: '< 2500ms',
                                message: 'Largest Contentful Paint needs improvement',
                            });
                        }
                    }

                    // CLS approximation
                    const clsEntries = performance.getEntriesByType('layout-shift');
                    if (clsEntries.length > 0) {
                        const cls = clsEntries.reduce((sum, e) => sum + (e.hadRecentInput ? 0 : e.value), 0);
                        result.metrics.cls = Math.round(cls * 1000) / 1000;

                        if (result.metrics.cls > 0.25) {
                            result.issues.push({
                                severity: 'high',
                                metric: 'CLS',
                                value: result.metrics.cls,
                                threshold: '< 0.1 good, < 0.25 needs improvement',
                                message: 'Cumulative Layout Shift is poor',
                            });
                            result.recommendations.push('Set explicit dimensions on images/embeds');
                        } else if (result.metrics.cls > 0.1) {
                            result.issues.push({
                                severity: 'medium',
                                metric: 'CLS',
                                value: result.metrics.cls,
                                threshold: '< 0.1',
                                message: 'Cumulative Layout Shift needs improvement',
                            });
                        }
                    }

                    // Score calculation
                    let score = 100;
                    result.issues.forEach(issue => {
                        if (issue.severity === 'high') score -= 20;
                        else if (issue.severity === 'medium') score -= 10;
                        else score -= 5;
                    });
                    result.score = Math.max(0, score);

                    // Grade
                    if (result.score >= 90) result.grade = 'A';
                    else if (result.score >= 80) result.grade = 'B';
                    else if (result.score >= 70) result.grade = 'C';
                    else if (result.score >= 60) result.grade = 'D';
                    else result.grade = 'F';

                    return result;
                }
            """)

            return json.dumps(analysis, indent=2)

        except Exception as e:
            return f"Error analyzing performance: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_memory_info() -> str:
        """
        Get detailed memory usage information.

        Returns:
            JSON object with memory metrics
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            import json

            # Get JS memory from page
            js_memory = await session.page.evaluate("""
                () => {
                    if (performance.memory) {
                        return {
                            js_heap_size_limit_mb: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024),
                            total_js_heap_size_mb: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
                            used_js_heap_size_mb: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
                        };
                    }
                    return null;
                }
            """)

            # Get detailed metrics via CDP
            try:
                client = await session.page.context.new_cdp_session(session.page)
                await client.send("Performance.enable", {})
                result = await client.send("Performance.getMetrics", {})

                cdp_memory = {}
                for metric in result.get("metrics", []):
                    name = metric["name"]
                    if "Heap" in name or "Memory" in name:
                        cdp_memory[name] = round(metric["value"] / 1024 / 1024, 2)

            except Exception:
                cdp_memory = None

            memory_info = {
                "javascript": js_memory,
                "detailed": cdp_memory,
            }

            return json.dumps(memory_info, indent=2)

        except Exception as e:
            return f"Error getting memory info: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_long_tasks() -> str:
        """
        Get long tasks that may cause jank or responsiveness issues.

        Long tasks are JavaScript tasks that take more than 50ms,
        which can block the main thread and cause poor user experience.

        Returns:
            JSON array of long tasks with timing information
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            import json

            # Set up observer and collect long tasks
            long_tasks = await session.page.evaluate("""
                () => {
                    const entries = performance.getEntriesByType('longtask');
                    return entries.map(e => ({
                        name: e.name,
                        start_time_ms: Math.round(e.startTime),
                        duration_ms: Math.round(e.duration),
                        attribution: e.attribution ? e.attribution.map(a => ({
                            name: a.name,
                            container_type: a.containerType,
                            container_name: a.containerName,
                        })) : [],
                    }));
                }
            """)

            total_blocking = sum(max(0, t["duration_ms"] - 50) for t in long_tasks)

            result = {
                "count": len(long_tasks),
                "total_blocking_time_ms": total_blocking,
                "tasks": long_tasks,
            }

            if total_blocking > 300:
                result["warning"] = "High Total Blocking Time may impact interactivity"

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting long tasks: {str(e)}"
