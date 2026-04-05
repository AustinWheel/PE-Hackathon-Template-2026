import { INSTANCES } from "@/lib/config";
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const instanceId = request.nextUrl.searchParams.get("instance");
  const instance = INSTANCES.find((i) => i.id === instanceId) || INSTANCES[0];
  const body = await request.json();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const res = await fetch(`${instance.url}/alerts/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "Flask unreachable" },
      { status: 502 }
    );
  } finally {
    clearTimeout(timeout);
  }
}
