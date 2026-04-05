"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import { parseLokiResponse, type LokiResponse, type LogEntry } from "@/lib/loki";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

const LEVEL_COLORS: Record<string, string> = {
  ERROR: "bg-red-500/20 text-red-400 border-red-500/30",
  WARNING: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  INFO: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  DEBUG: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const METHOD_COLORS: Record<string, string> = {
  GET: "text-blue-400",
  POST: "text-green-400",
  PUT: "text-yellow-400",
  DELETE: "text-red-400",
};

interface ServiceFilter {
  id: string;
  label: string;
  pathMatch: string;
}

const SERVICE_FILTERS: ServiceFilter[] = [
  { id: "all", label: "All", pathMatch: "" },
  { id: "health", label: "Health", pathMatch: "/health" },
  { id: "users", label: "Users", pathMatch: "/users" },
  { id: "urls", label: "URLs", pathMatch: "/urls" },
  { id: "redirects", label: "Redirects", pathMatch: "/r/" },
  { id: "events", label: "Events", pathMatch: "/events" },
  { id: "alerts", label: "Alerts", pathMatch: "/alerts" },
  { id: "chaos", label: "Chaos", pathMatch: "/chaos" },
  { id: "products", label: "Products", pathMatch: "/products" },
];

function buildLogQuery(filters: {
  region: string;
  environment: string;
  level: string;
  search: string;
  servicePath: string;
}): string {
  const labelParts = ['job="flask-app"'];
  if (filters.region !== "all") {
    labelParts.push(`region="${filters.region}"`);
  }
  if (filters.environment !== "all") {
    labelParts.push(`environment="${filters.environment}"`);
  }

  let query = `{${labelParts.join(", ")}}`;

  // Add pipeline filters
  const pipelineParts: string[] = [];

  if (filters.servicePath) {
    const escaped = filters.servicePath.replace("/", "\\/");
    pipelineParts.push('|~ "' + '"path":\\\\s*"' + escaped + '"');
  }

  if (filters.search) {
    pipelineParts.push("|= `" + filters.search + "`");
  }

  if (filters.level !== "all") {
    pipelineParts.push("| json | level=~`(?i)" + filters.level + "`");
  }

  return query + " " + pipelineParts.join(" ");
}

function LogRow({ entry }: { entry: LogEntry }) {
  const [expanded, setExpanded] = useState(false);

  const method = entry.parsed?.method as string | undefined;
  const path = entry.parsed?.path as string | undefined;
  const status = entry.parsed?.status as number | undefined;

  return (
    <div
      className="cursor-pointer border-b border-border/50 px-3 py-2 transition-colors hover:bg-muted/30"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center gap-2.5">
        <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
          {format(entry.timestamp, "HH:mm:ss.SSS")}
        </span>
        <Badge
          variant="outline"
          className={cn("shrink-0 text-[10px] px-1.5 py-0", LEVEL_COLORS[entry.level] || "")}
        >
          {entry.level}
        </Badge>
        {entry.labels.region && (
          <span className="shrink-0 text-[10px] text-muted-foreground font-mono">
            {entry.labels.region}
          </span>
        )}
        {method && (
          <span className={cn("shrink-0 text-[11px] font-mono font-medium", METHOD_COLORS[method] || "")}>
            {method}
          </span>
        )}
        {path && (
          <span className="shrink-0 text-[11px] font-mono text-muted-foreground">
            {path}
          </span>
        )}
        {status !== undefined && (
          <span className={cn(
            "shrink-0 text-[11px] font-mono",
            status >= 500 ? "text-red-400" : status >= 400 ? "text-yellow-400" : "text-green-400"
          )}>
            {status}
          </span>
        )}
        <span className="truncate text-[13px]">{entry.message}</span>
      </div>
      {expanded && entry.parsed && (
        <pre className="mt-2 overflow-auto rounded bg-muted/50 p-3 text-[11px] font-mono">
          {JSON.stringify(entry.parsed, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function LogsPage() {
  const [search, setSearch] = useState("");
  const [region, setRegion] = useState("all");
  const [environment, setEnvironment] = useState("all");
  const [level, setLevel] = useState("all");
  const [activeService, setActiveService] = useState("all");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const serviceFilter = SERVICE_FILTERS.find((s) => s.id === activeService);
  const query = buildLogQuery({
    region,
    environment,
    level,
    search,
    servicePath: serviceFilter?.pathMatch || "",
  });
  const params = new URLSearchParams({ query, limit: "200" });

  const { data, isLoading } = useSWR<LokiResponse>(
    `/api/loki?${params}`,
    fetcher,
    { refreshInterval: autoRefresh ? 5000 : 0 }
  );

  const entries = data ? parseLokiResponse(data) : [];

  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col">
      <div className="mb-4">
        <h1 className="text-xl font-semibold">Log Explorer</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Search and filter logs by service, endpoint, and level
        </p>
      </div>

      {/* Service tabs */}
      <div className="mb-4">
        <Tabs value={activeService} onValueChange={(v) => v != null && setActiveService(String(v))}>
          <TabsList>
            {SERVICE_FILTERS.map((s) => (
              <TabsTrigger key={s.id} value={s.id}>
                {s.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Filters */}
      <Card className="mb-4">
        <CardContent className="flex flex-wrap items-center gap-3 pt-4">
          <Input
            placeholder="Search logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-56"
          />
          <Select value={region} onValueChange={(v) => v && setRegion(v)}>
            <SelectTrigger className="w-[110px]">
              <SelectValue placeholder="Region" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Regions</SelectItem>
              <SelectItem value="nyc">NYC</SelectItem>
              <SelectItem value="sfo">SFO</SelectItem>
            </SelectContent>
          </Select>
          <Select value={environment} onValueChange={(v) => v && setEnvironment(v)}>
            <SelectTrigger className="w-[110px]">
              <SelectValue placeholder="Env" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Envs</SelectItem>
              <SelectItem value="prod">Production</SelectItem>
              <SelectItem value="staging">Staging</SelectItem>
            </SelectContent>
          </Select>
          <Select value={level} onValueChange={(v) => v && setLevel(v)}>
            <SelectTrigger className="w-[110px]">
              <SelectValue placeholder="Level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Levels</SelectItem>
              <SelectItem value="ERROR">Error</SelectItem>
              <SelectItem value="WARNING">Warning</SelectItem>
              <SelectItem value="INFO">Info</SelectItem>
              <SelectItem value="DEBUG">Debug</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex items-center gap-2">
            <Switch
              id="auto-refresh"
              checked={autoRefresh}
              onCheckedChange={setAutoRefresh}
            />
            <Label htmlFor="auto-refresh" className="text-[13px]">
              Live
            </Label>
          </div>
          <Badge variant="outline" className="ml-auto text-[11px]">
            {entries.length} entries
          </Badge>
        </CardContent>
      </Card>

      {/* Log stream */}
      <Card className="flex-1 overflow-hidden">
        <CardHeader className="pb-1">
          <CardTitle className="text-[13px] font-medium">
            {serviceFilter?.id === "all" ? "All Services" : serviceFilter?.label} — Log Stream
          </CardTitle>
        </CardHeader>
        <ScrollArea className="h-[calc(100vh-20rem)]">
          {isLoading ? (
            <div className="flex h-32 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
            </div>
          ) : entries.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-[13px] text-muted-foreground">
              No logs found
            </div>
          ) : (
            entries.map((entry, i) => <LogRow key={`${entry.nanoseconds}-${i}`} entry={entry} />)
          )}
        </ScrollArea>
      </Card>
    </div>
  );
}
