import { proxyFormulario } from "@/lib/api";

export const dynamic = "force-dynamic";

export function POST(req: Request) {
  return proxyFormulario("valores", req);
}
