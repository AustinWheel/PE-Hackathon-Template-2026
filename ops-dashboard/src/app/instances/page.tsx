"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import { formatDuration } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface InstanceHealth {
  instanceId: string;
  status: string;
  version: string;
  uptime_seconds: number;
  database: string;
  latencyMs: number;
}

interface Cluster {
  id: string;
  name: string;
  region: string;
  env: string;
  instances: InstanceHealth[];
  error: string | null;
}

interface HealthResponse {
  clusters: Cluster[];
}

function statusColor(status: string) {
  if (status === "ok") return "bg-green-500";
  if (status === "degraded") return "bg-yellow-500";
  return "bg-red-500";
}

function statusBorder(status: string) {
  if (status === "ok") return "border-green-500/60 hover:border-green-400";
  if (status === "degraded") return "border-yellow-500/60 hover:border-yellow-400";
  return "border-red-500/60 hover:border-red-400";
}

function clusterStatus(instances: InstanceHealth[]) {
  if (instances.length === 0) return "down";
  if (instances.every((i) => i.status === "ok")) return "ok";
  if (instances.some((i) => i.status === "ok")) return "degraded";
  return "down";
}

export default function InstancesPage() {
  const [selected, setSelected] = useState<{
    clusterId: string;
    instanceId: string;
  } | null>(null);

  const { data, error, isLoading } = useSWR<HealthResponse>(
    "/api/health",
    fetcher,
    { refreshInterval: 15000 }
  );

  const selectedInstance =
    data && selected
      ? data.clusters
          .find((c) => c.id === selected.clusterId)
          ?.instances.find((i) => i.instanceId === selected.instanceId)
      : null;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Instance Overview</h1>
        <p className="text-sm text-muted-foreground">
          Clusters across all regions and environments
        </p>
      </div>

      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="mb-2 h-5 w-32 rounded bg-muted" />
              <div className="h-20 rounded-lg bg-muted" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">
              Failed to fetch health data: {error.message}
            </p>
          </CardContent>
        </Card>
      )}

      {data && (
        <div className="space-y-6">
          {data.clusters.map((cluster) => {
            const status = clusterStatus(cluster.instances);
            return (
              <div key={cluster.id}>
                <div className="mb-2 flex items-center gap-3">
                  <div
                    className={cn("h-2.5 w-2.5 rounded-full", statusColor(status))}
                  />
                  <Badge
                    variant={cluster.env === "prod" ? "default" : "secondary"}
                  >
                    {cluster.env}
                  </Badge>
                  <Badge variant="outline">
                    {cluster.region.toUpperCase()}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {cluster.name}
                  </span>
                  <Badge variant="outline" className="ml-auto text-xs">
                    {cluster.instances.length} instance
                    {cluster.instances.length !== 1 ? "s" : ""}
                  </Badge>
                </div>

                <Card>
                  <CardContent className="py-4">
                    {cluster.error ? (
                      <p className="text-sm text-red-400">{cluster.error}</p>
                    ) : (
                      <div className="flex flex-wrap gap-3">
                        {cluster.instances.map((inst) => {
                          const isSelected =
                            selected?.clusterId === cluster.id &&
                            selected?.instanceId === inst.instanceId;
                          return (
                            <button
                              key={inst.instanceId}
                              onClick={() =>
                                setSelected(
                                  isSelected
                                    ? null
                                    : {
                                        clusterId: cluster.id,
                                        instanceId: inst.instanceId,
                                      }
                                )
                              }
                              className={cn(
                                "flex items-center gap-2 rounded-md border-2 px-3 py-2 text-left transition-all",
                                statusBorder(inst.status),
                                isSelected
                                  ? "bg-accent ring-1 ring-ring"
                                  : "bg-card hover:bg-accent/50"
                              )}
                            >
                              <div
                                className={cn(
                                  "h-2 w-2 rounded-full",
                                  statusColor(inst.status)
                                )}
                              />
                              <span className="font-mono text-sm">
                                {inst.instanceId}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Detail panel for selected instance in this cluster */}
                {selected?.clusterId === cluster.id && selectedInstance && (
                  <Card className="mt-2 border-accent">
                    <CardContent className="py-4">
                      <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm md:grid-cols-5">
                        <div>
                          <span className="text-muted-foreground">
                            Instance
                          </span>
                          <p className="font-mono">
                            {selectedInstance.instanceId}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Status</span>
                          <p className="flex items-center gap-1.5">
                            <span
                              className={cn(
                                "inline-block h-2 w-2 rounded-full",
                                statusColor(selectedInstance.status)
                              )}
                            />
                            {selectedInstance.status}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Uptime</span>
                          <p className="font-mono">
                            {formatDuration(selectedInstance.uptime_seconds)}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Version</span>
                          <p className="font-mono">
                            {selectedInstance.version}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">
                            Database
                          </span>
                          <p
                            className={cn(
                              "font-mono",
                              selectedInstance.database === "connected"
                                ? "text-green-400"
                                : "text-red-400"
                            )}
                          >
                            {selectedInstance.database}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Latency</span>
                          <p className="font-mono">
                            {selectedInstance.latencyMs}ms
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
