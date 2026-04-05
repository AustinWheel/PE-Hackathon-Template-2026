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

const COLORS = ["#22c55e", "#3b82f6", "#eab308", "#ef4444", "#a855f7"];

const QUERIES = {
  traffic: "sum(rate(http_requests_total[1m])) by (job)",
  errorRate: "(sum by (job) (rate(http_errors_total[2m])) / clamp_min(sum by (job) (rate(http_requests_total[2m])), 0.001)) * 100",
  latencyP95: "histogram_quantile(0.95, sum by (le, job) (rate(http_request_duration_seconds_bucket[5m])))",
  latencyP50: "histogram_quantile(0.50, sum by (le, job) (rate(http_request_duration_seconds_bucket[5m])))",
  cpu: "system_cpu_percent",
  memory: "system_memory_percent",
};

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
}: {
  title: string;
  query: string;
  range: string;
  unit?: string;
  type?: "line" | "area";
}) {
  const { data, isLoading, error: fetchError } = usePrometheus(query, range);
  const chartData = data ? parsePrometheusResponse(data) : [];
  const series = chartData.length
    ? Object.keys(chartData[0]).filter((k) => k !== "time")
    : [];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex h-[200px] items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
          </div>
        ) : fetchError ? (
          <div className="flex h-[200px] items-center justify-center text-sm text-destructive">
            Failed to load
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
            No data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            {type === "area" ? (
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                  dataKey="time"
                  tickFormatter={formatTick}
                  stroke="#666"
                  fontSize={11}
                />
                <YAxis
                  stroke="#666"
                  fontSize={11}
                  tickFormatter={(v) =>
                    unit ? `${v.toFixed(1)}${unit}` : v.toFixed(2)
                  }
                />
                <Tooltip
                  contentStyle={{
                    background: "#1a1a1a",
                    border: "1px solid #333",
                    borderRadius: "6px",
                    fontSize: 12,
                  }}
                  labelFormatter={(v) =>
                    format(new Date(v as number), "HH:mm:ss")
                  }
                  formatter={(value) => [
                    `${Number(value).toFixed(2)}${unit || ""}`,
                  ]}
                />
                <Legend />
                {series.map((s, i) => (
                  <Area
                    key={s}
                    type="monotone"
                    dataKey={s}
                    stroke={COLORS[i % COLORS.length]}
                    fill={COLORS[i % COLORS.length]}
                    fillOpacity={0.1}
                    strokeWidth={1.5}
                  />
                ))}
              </AreaChart>
            ) : (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                  dataKey="time"
                  tickFormatter={formatTick}
                  stroke="#666"
                  fontSize={11}
                />
                <YAxis
                  stroke="#666"
                  fontSize={11}
                  tickFormatter={(v) =>
                    unit ? `${v.toFixed(1)}${unit}` : v.toFixed(2)
                  }
                />
                <Tooltip
                  contentStyle={{
                    background: "#1a1a1a",
                    border: "1px solid #333",
                    borderRadius: "6px",
                    fontSize: 12,
                  }}
                  labelFormatter={(v) =>
                    format(new Date(v as number), "HH:mm:ss")
                  }
                  formatter={(value) => [
                    `${Number(value).toFixed(2)}${unit || ""}`,
                  ]}
                />
                <Legend />
                {series.map((s, i) => (
                  <Line
                    key={s}
                    type="monotone"
                    dataKey={s}
                    stroke={COLORS[i % COLORS.length]}
                    strokeWidth={1.5}
                    dot={false}
                  />
                ))}
              </LineChart>
            )}
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default function MetricsPage() {
  const [range, setRange] = useState("1h");
  const [_region, setRegion] = useState("all");

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Metrics Dashboard</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Real-time application and system metrics from Prometheus
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={_region} onValueChange={(v) => v && setRegion(v)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Regions</SelectItem>
              <SelectItem value="nyc">NYC</SelectItem>
              <SelectItem value="sfo">SFO</SelectItem>
            </SelectContent>
          </Select>
          <Tabs value={range} onValueChange={setRange}>
            <TabsList>
              <TabsTrigger value="15m">15m</TabsTrigger>
              <TabsTrigger value="1h">1h</TabsTrigger>
              <TabsTrigger value="6h">6h</TabsTrigger>
              <TabsTrigger value="24h">24h</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MetricChart
          title="Traffic (req/s)"
          query={QUERIES.traffic}
          range={range}
          unit=" req/s"
          type="area"
        />
        <MetricChart
          title="Error Rate (%)"
          query={QUERIES.errorRate}
          range={range}
          unit="%"
          type="area"
        />
        <MetricChart
          title="Latency P95 (seconds)"
          query={QUERIES.latencyP95}
          range={range}
          unit="s"
        />
        <MetricChart
          title="CPU Usage (%)"
          query={QUERIES.cpu}
          range={range}
          unit="%"
        />
        <MetricChart
          title="Memory Usage (%)"
          query={QUERIES.memory}
          range={range}
          unit="%"
        />
        <MetricChart
          title="Latency P50 (seconds)"
          query={QUERIES.latencyP50}
          range={range}
          unit="s"
        />
      </div>
    </div>
  );
}
