"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import {
  parsePrometheusResponse,
  buildQueryParams,
  type PrometheusResponse,
} from "@/lib/prometheus";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

const COLORS = ["#22c55e", "#3b82f6", "#eab308", "#ef4444", "#a855f7"];

interface Endpoint {
  id: string;
  label: string;
  method: string;
  filter: string;
}

interface Service {
  id: string;
  label: string;
  allFilter: string;
  endpoints: Endpoint[];
}

const SERVICES: Service[] = [
  {
    id: "health",
    label: "Health",
    allFilter: 'endpoint="/health"',
    endpoints: [
      { id: "get-health", label: "GET /health", method: "GET", filter: 'method="GET",endpoint="/health"' },
    ],
  },
  {
    id: "users",
    label: "Users",
    allFilter: 'endpoint=~"/users.*"',
    endpoints: [
      { id: "get-users", label: "GET /users", method: "GET", filter: 'method="GET",endpoint="/users"' },
      { id: "post-users", label: "POST /users", method: "POST", filter: 'method="POST",endpoint="/users"' },
      { id: "get-user", label: "GET /users/:id", method: "GET", filter: 'method="GET",endpoint=~"/users/\\\\d+"' },
      { id: "put-user", label: "PUT /users/:id", method: "PUT", filter: 'method="PUT",endpoint=~"/users/\\\\d+"' },
    ],
  },
  {
    id: "urls",
    label: "URLs",
    allFilter: 'endpoint=~"/urls.*"',
    endpoints: [
      { id: "get-urls", label: "GET /urls", method: "GET", filter: 'method="GET",endpoint="/urls"' },
      { id: "post-urls", label: "POST /urls", method: "POST", filter: 'method="POST",endpoint="/urls"' },
      { id: "get-url", label: "GET /urls/:id", method: "GET", filter: 'method="GET",endpoint=~"/urls/\\\\d+"' },
      { id: "put-url", label: "PUT /urls/:id", method: "PUT", filter: 'method="PUT",endpoint=~"/urls/\\\\d+"' },
    ],
  },
  {
    id: "redirects",
    label: "Redirects",
    allFilter: 'endpoint=~"/r/.*"',
    endpoints: [
      { id: "get-redirect", label: "GET /r/:code", method: "GET", filter: 'method="GET",endpoint=~"/r/.*"' },
    ],
  },
  {
    id: "events",
    label: "Events",
    allFilter: 'endpoint="/events"',
    endpoints: [
      { id: "get-events", label: "GET /events", method: "GET", filter: 'method="GET",endpoint="/events"' },
    ],
  },
  {
    id: "alerts",
    label: "Alerts",
    allFilter: 'endpoint=~"/alerts.*"',
    endpoints: [
      { id: "get-alerts", label: "GET /alerts", method: "GET", filter: 'method="GET",endpoint="/alerts"' },
      { id: "post-alerts", label: "POST /alerts", method: "POST", filter: 'method="POST",endpoint="/alerts"' },
      { id: "put-alert", label: "PUT /alerts/:id", method: "PUT", filter: 'method="PUT",endpoint=~"/alerts/\\\\d+"' },
    ],
  },
  {
    id: "products",
    label: "Products",
    allFilter: 'endpoint="/products"',
    endpoints: [
      { id: "get-products", label: "GET /products", method: "GET", filter: 'method="GET",endpoint="/products"' },
    ],
  },
];

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  POST: "bg-green-500/20 text-green-400 border-green-500/30",
  PUT: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  DELETE: "bg-red-500/20 text-red-400 border-red-500/30",
};

function buildQueries(filter: string) {
  return {
    traffic: `sum by (job) (rate(http_requests_total{${filter}}[1m]))`,
    errors: `sum by (job) (rate(http_errors_total{${filter}}[1m]))`,
    avgLatency: `sum by (job) (rate(http_request_duration_seconds_sum{${filter}}[5m])) / clamp_min(sum by (job) (rate(http_request_duration_seconds_count{${filter}}[5m])), 0.001)`,
  };
}

type GroupBy = "job" | "region" | "environment";

function usePrometheus(query: string, range: string) {
  const params = buildQueryParams(query, range);
  return useSWR<PrometheusResponse>(
    `/api/prometheus?${params}`,
    fetcher,
    { refreshInterval: 30000 }
  );
}

function formatTick(ts: number) {
  return format(new Date(ts), "HH:mm");
}

function MetricChart({
  title,
  query,
  range,
  unit,
  type = "line",
  labelKey = "job",
  height = 160,
}: {
  title: string;
  query: string;
  range: string;
  unit?: string;
  type?: "line" | "area";
  labelKey?: string;
  height?: number;
}) {
  const { data, isLoading, error: fetchError } = usePrometheus(query, range);
  const chartData = data ? parsePrometheusResponse(data, labelKey) : [];
  const series = chartData.length
    ? Object.keys(chartData[0]).filter((k) => k !== "time")
    : [];

  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-[13px] font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center" style={{ height }}>
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
          </div>
        ) : fetchError ? (
          <div className="flex items-center justify-center text-[13px] text-destructive" style={{ height }}>
            Failed to load
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center text-[13px] text-muted-foreground" style={{ height }}>
            No data
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={height}>
            {type === "area" ? (
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="time" tickFormatter={formatTick} stroke="#555" fontSize={10} />
                <YAxis stroke="#555" fontSize={10} tickFormatter={(v) => unit ? `${v.toFixed(1)}${unit}` : v.toFixed(2)} />
                <Tooltip
                  contentStyle={{ background: "#1a1a1a", border: "1px solid #333", borderRadius: "6px", fontSize: 11 }}
                  labelFormatter={(v) => format(new Date(v as number), "HH:mm:ss")}
                  formatter={(value) => [`${Number(value).toFixed(3)}${unit || ""}`]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {series.map((s, i) => (
                  <Area key={s} type="monotone" dataKey={s} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.1} strokeWidth={1.5} />
                ))}
              </AreaChart>
            ) : (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="time" tickFormatter={formatTick} stroke="#555" fontSize={10} />
                <YAxis stroke="#555" fontSize={10} tickFormatter={(v) => unit ? `${v.toFixed(1)}${unit}` : v.toFixed(2)} />
                <Tooltip
                  contentStyle={{ background: "#1a1a1a", border: "1px solid #333", borderRadius: "6px", fontSize: 11 }}
                  labelFormatter={(v) => format(new Date(v as number), "HH:mm:ss")}
                  formatter={(value) => [`${Number(value).toFixed(3)}${unit || ""}`]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {series.map((s, i) => (
                  <Line key={s} type="monotone" dataKey={s} stroke={COLORS[i % COLORS.length]} strokeWidth={1.5} dot={false} />
                ))}
              </LineChart>
            )}
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

function EndpointRow({
  endpoint,
  range,
}: {
  endpoint: Endpoint;
  range: string;
}) {
  const queries = buildQueries(endpoint.filter);
  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center gap-2">
        <Badge variant="outline" className={cn("text-[10px] font-mono", METHOD_COLORS[endpoint.method])}>
          {endpoint.method}
        </Badge>
        <span className="text-[13px] font-medium font-mono">{endpoint.label.replace(`${endpoint.method} `, "")}</span>
      </div>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <MetricChart title="Traffic (req/s)" query={queries.traffic} range={range} unit=" req/s" type="area" height={140} />
        <MetricChart title="Errors (err/s)" query={queries.errors} range={range} unit=" err/s" type="area" height={140} />
        <MetricChart title="Avg Latency (s)" query={queries.avgLatency} range={range} unit="s" height={140} />
      </div>
    </div>
  );
}

export default function MetricsPage() {
  const [range, setRange] = useState("1h");
  const [activeService, setActiveService] = useState("users");
  const [systemGroupBy, setSystemGroupBy] = useState<GroupBy>("job");

  const service = SERVICES.find((s) => s.id === activeService) || SERVICES[0];
  const overviewQueries = buildQueries(service.allFilter);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Metrics Dashboard</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Per-endpoint metrics and system resource usage
          </p>
        </div>
        <Tabs value={range} onValueChange={setRange}>
          <TabsList>
            <TabsTrigger value="15m">15m</TabsTrigger>
            <TabsTrigger value="1h">1h</TabsTrigger>
            <TabsTrigger value="6h">6h</TabsTrigger>
            <TabsTrigger value="24h">24h</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Service tabs */}
      <div className="mb-5">
        <Tabs value={activeService} onValueChange={(v) => v != null && setActiveService(String(v))}>
          <TabsList>
            {SERVICES.map((s) => (
              <TabsTrigger key={s.id} value={s.id}>
                {s.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Service overview */}
      <div className="mb-6">
        <h2 className="mb-3 text-[13px] font-medium text-muted-foreground">
          {service.label} — All Endpoints
        </h2>
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <MetricChart title="Total Traffic (req/s)" query={overviewQueries.traffic} range={range} unit=" req/s" type="area" height={150} />
          <MetricChart title="Total Errors (err/s)" query={overviewQueries.errors} range={range} unit=" err/s" type="area" height={150} />
          <MetricChart title="Avg Latency (s)" query={overviewQueries.avgLatency} range={range} unit="s" height={150} />
        </div>
      </div>

      {/* Per-endpoint breakdown */}
      {service.endpoints.length > 1 && (
        <div className="mb-8">
          <h2 className="mb-4 text-[13px] font-medium text-muted-foreground">
            Endpoint Breakdown
          </h2>
          {service.endpoints.map((ep) => (
            <EndpointRow key={ep.id} endpoint={ep} range={range} />
          ))}
        </div>
      )}

      {/* System metrics */}
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[13px] font-medium text-muted-foreground">System Metrics</h2>
        <Select value={systemGroupBy} onValueChange={(v) => v && setSystemGroupBy(v as GroupBy)}>
          <SelectTrigger className="w-[150px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="job">By Instance</SelectItem>
            <SelectItem value="region">By Region</SelectItem>
            <SelectItem value="environment">By Environment</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MetricChart title="CPU Usage (%)" query="system_cpu_percent" range={range} unit="%" labelKey={systemGroupBy} />
        <MetricChart title="Memory Usage (%)" query="system_memory_percent" range={range} unit="%" labelKey={systemGroupBy} />
      </div>
    </div>
  );
}
