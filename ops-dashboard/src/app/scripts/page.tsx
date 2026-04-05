"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import {
  parsePrometheusResponse,
  buildQueryParams,
  type PrometheusResponse,
} from "@/lib/prometheus";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Activity, Bot } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const COLORS = ["#22c55e", "#3b82f6", "#eab308", "#ef4444", "#a855f7", "#06b6d4", "#f97316", "#ec4899"];

const TRAFFIC_CONFIG = {
  targets: [
    "pe-hackathon-muy5v.ondigitalocean.app (Prod NYC)",
    "pe-hackathon-prod-sfo-wkpqr.ondigitalocean.app (Prod SFO)",
    "pe-hackathon-staging-f28oj.ondigitalocean.app (Staging)",
  ],
  interval: "3 seconds",
  operations: [
    "GET /health (x3)",
    "GET /metrics",
    "GET /users, POST /users (x3)",
    "GET /users/:id, PUT /users/:id",
    "POST /users (bad — 400)",
    "GET /users/999999 (404)",
    "POST /urls (x6), GET /urls",
    "GET /urls/:id, PUT /urls/:id",
    "PUT /urls/:id (deactivate)",
    "GET /r/:code (x4 + 410 + 404)",
    "GET /events (x2)",
    "GET /products",
    "GET /alerts, POST /alerts",
    "PUT /alerts/:id (ack + resolve)",
    "GET /logs, GET /logs?level=ERROR",
  ],
  script: "scripts/synthetic_traffic.py",
};

const CHAOS_CONFIG = {
  targets: ["Prod NYC", "Prod SFO"],
  interval: "5 minutes",
  actions: [
    "500/502/503 errors (weighted)",
    "Latency injection (2s/5s/10s)",
    "CPU spikes (5s/15s)",
    "Error floods (10/30 count)",
    "Health check failure (503)",
  ],
  script: "scripts/chaos_monkey.py",
  alertCheck: "Waits 90s after floods/health-fail, then checks AlertManager",
};

// Endpoint to query label mapping for the traffic breakdown chart
const ENDPOINT_GROUPS = [
  { label: "/health", filter: 'endpoint="/health"' },
  { label: "/users*", filter: 'endpoint=~"/users.*"' },
  { label: "/urls*", filter: 'endpoint=~"/urls.*"' },
  { label: "/r/*", filter: 'endpoint=~"/r/.*"' },
  { label: "/events", filter: 'endpoint="/events"' },
  { label: "/alerts*", filter: 'endpoint=~"/alerts.*"' },
  { label: "/products", filter: 'endpoint="/products"' },
  { label: "/logs", filter: 'endpoint=~"/logs.*"' },
];

function TrafficBreakdownChart() {
  // Build a query that gets total request count per endpoint group
  const queries = ENDPOINT_GROUPS.map((g) =>
    `sum(increase(http_requests_total{${g.filter}}[15m]))`
  );

  // Fetch each independently
  const results = ENDPOINT_GROUPS.map((g, i) => {
    const params = buildQueryParams(queries[i], "15m");
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const { data } = useSWR<PrometheusResponse>(
      `/api/prometheus?${params.toString().replace("query_range", "query")}`,
      fetcher,
      { refreshInterval: 30000 }
    );
    const parsed = data ? parsePrometheusResponse(data) : [];
    const lastVal = parsed.length > 0 ? Object.values(parsed[parsed.length - 1]).reduce<number>((sum, v) => typeof v === "number" && v !== parsed[parsed.length - 1].time ? sum + v : sum, 0) : 0;
    return { label: g.label, value: lastVal };
  });

  const total = results.reduce((s, r) => s + r.value, 0);
  const chartData = results
    .filter((r) => r.value > 0)
    .map((r) => ({ ...r, pct: total > 0 ? ((r.value / total) * 100).toFixed(1) : "0" }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-[13px] font-medium">Traffic Breakdown (last 15m)</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-[13px] text-muted-foreground">
            Loading...
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 60 }}>
                <XAxis type="number" fontSize={10} stroke="#555" />
                <YAxis type="category" dataKey="label" fontSize={11} stroke="#555" width={55} />
                <Tooltip
                  contentStyle={{ background: "#1a1a1a", border: "1px solid #333", borderRadius: "6px", fontSize: 11 }}
                  formatter={(value) => [
                    `${Math.round(Number(value))} reqs`,
                  ]}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {chartData.map((_entry, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-2 text-center text-[11px] text-muted-foreground">
              Total: {Math.round(total)} requests in last 15 minutes
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function ScriptsPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Synthetic Traffic & Chaos Monkey</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Background scripts that generate traffic and test resilience
        </p>
      </div>

      {/* Traffic breakdown chart */}
      <div className="mb-6">
        <TrafficBreakdownChart />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-green-400" />
              <CardTitle className="text-base">Synthetic Traffic Generator</CardTitle>
            </div>
            <CardDescription>
              High-volume traffic with full endpoint coverage including error-producing actions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-muted-foreground">Status</span>
              <Badge
                variant="outline"
                className="bg-green-500/20 text-green-400 border-green-500/30"
              >
                Running
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-muted-foreground">Interval</span>
              <span className="text-[13px] font-mono">{TRAFFIC_CONFIG.interval}</span>
            </div>
            <div>
              <span className="text-[13px] text-muted-foreground">Targets</span>
              <div className="mt-1 space-y-1">
                {TRAFFIC_CONFIG.targets.map((t) => (
                  <div key={t} className="text-[11px] font-mono text-muted-foreground">
                    {t}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <span className="text-[13px] text-muted-foreground">Operations per cycle</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {TRAFFIC_CONFIG.operations.map((op) => (
                  <Badge key={op} variant="outline" className="text-[10px]">
                    {op}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between border-t border-border/50 pt-3">
              <code className="text-[11px] text-muted-foreground">
                {TRAFFIC_CONFIG.script}
              </code>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Stop</Button>
                <Button size="sm">Start</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-red-400" />
              <CardTitle className="text-base">Chaos Monkey</CardTitle>
            </div>
            <CardDescription>
              Automated failure injection every 5 minutes with weighted action selection
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-muted-foreground">Status</span>
              <Badge
                variant="outline"
                className="bg-green-500/20 text-green-400 border-green-500/30"
              >
                Running
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-muted-foreground">Interval</span>
              <span className="text-[13px] font-mono">{CHAOS_CONFIG.interval}</span>
            </div>
            <div>
              <span className="text-[13px] text-muted-foreground">Targets</span>
              <div className="mt-1 space-y-1">
                {CHAOS_CONFIG.targets.map((t) => (
                  <div key={t} className="text-[11px] font-mono text-muted-foreground">
                    {t}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <span className="text-[13px] text-muted-foreground">Chaos Actions</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {CHAOS_CONFIG.actions.map((a) => (
                  <Badge key={a} variant="outline" className="text-[10px]">
                    {a}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="text-[11px] text-muted-foreground">
              {CHAOS_CONFIG.alertCheck}
            </div>
            <div className="flex items-center justify-between border-t border-border/50 pt-3">
              <code className="text-[11px] text-muted-foreground">
                {CHAOS_CONFIG.script}
              </code>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Stop</Button>
                <Button size="sm">Start</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
