import { proxyFormulario } from "@/lib/api";

export const dynamic = "force-dynamic";

export function GET(req: Request) {
  return proxyFormulario("acesso", req);
}
