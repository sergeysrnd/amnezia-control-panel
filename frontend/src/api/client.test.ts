import { afterEach, describe, expect, it, vi } from "vitest";

import { createConnection, deleteConnection, MutationApiError } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("management API", () => {
  it("uses the session token and sends the revision and operation id", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ token: "session-token" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "committed", filename: "test.conf", native_config: "test-profile" })));
    vi.stubGlobal("fetch", fetcher);
    const input = { protocol: "wireguard" as const, name: "Phone", revision: "version", keepalive: true, operation_id: "operation" };
    const result = await createConnection(input);
    expect(result).toEqual({ filename: "test.conf", nativeConfig: "test-profile" });
    const [url, options] = fetcher.mock.calls[1] as [string, RequestInit];
    expect(url).toBe("/api/v1/protocols/wireguard/peers");
    expect(options.method).toBe("POST");
    expect(options.headers).toMatchObject({ "X-Amnezia-Token": "session-token" });
    expect(JSON.parse(options.body as string)).toEqual({ name: "Phone", revision: "version", keepalive: true, operation_id: "operation" });
  });

  it("does not retry a conflicting or uncertain mutation", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ token: "session-token" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: "revision_conflict" }), { status: 409 }));
    vi.stubGlobal("fetch", fetcher);
    await expect(deleteConnection("awg", "peer", { name: "Phone", revision: "old", operation_id: "operation" })).rejects.toBeInstanceOf(MutationApiError);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("does not pretend a replay contains a downloadable key", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ token: "session-token" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "committed", replayed: true }))));
    await expect(createConnection({ protocol: "awg", name: "Phone", revision: "v", keepalive: false, operation_id: "op" })).rejects.toThrow("один раз");
  });
});
