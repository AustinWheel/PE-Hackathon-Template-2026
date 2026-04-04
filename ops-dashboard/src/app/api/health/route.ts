import { INSTANCES } from "@/lib/config";

export const dynamic = "force-dynamic";

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
  url: string;
  instances: InstanceHealth[];
  error: string | null;
}

async function probeInstance(
  url: string
): Promise<{ data: Record<string, unknown>; latencyMs: number } | null> {
  const start = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(`${url}/health`, {
      signal: controller.signal,
      cache: "no-store",
    });
    const latencyMs = Date.now() - start;
    const data = await res.json();
    return { data, latencyMs };
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

export async function GET() {
  const clusters: Cluster[] = await Promise.all(
    INSTANCES.map(async (inst) => {
      // Make 12 parallel requests to discover instances behind the LB
      const probes = await Promise.allSettled(
        Array.from({ length: 12 }, () => probeInstance(inst.url))
      );

      const seen = new Map<string, InstanceHealth>();

      for (const probe of probes) {
        if (probe.status !== "fulfilled" || !probe.value) continue;
        const { data, latencyMs } = probe.value;
        const id = (data.instance_id as string) || "unknown";
        if (seen.has(id)) continue;
        seen.set(id, {
          instanceId: id,
          status: (data.status as string) || "unknown",
          version: (data.version as string) || "?",
          uptime_seconds: (data.uptime_seconds as number) || 0,
          database: (data.database as string) || "unknown",
          latencyMs,
        });
      }

      return {
        id: inst.id,
        name: inst.name,
        region: inst.region,
        env: inst.env,
        url: inst.url,
        instances: Array.from(seen.values()),
        error: seen.size === 0 ? "All probes failed" : null,
      };
    })
  );

  return Response.json({ clusters });
}
