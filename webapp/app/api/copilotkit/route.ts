import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

// The ADK agent is served natively as an AG-UI endpoint by the Python
// `ag-ui-adk` middleware (agent/server.py → POST /chat). We connect to it
// directly with an HttpAgent — no custom factory, no BFF translation. This is
// the whole point of the native integration vs the sibling "lite" repo.
const ADK_AGUI_URL = process.env.ADK_AGUI_URL ?? "http://localhost:8000/chat";

const runtime = new CopilotRuntime({
  agents: {
    default: new HttpAgent({ url: ADK_AGUI_URL }),
  },
  // Dynamic A2UI: the middleware injects a `render_a2ui` tool (+ guidelines +
  // our frontend catalog schema) into the agent at request time. The LLM
  // decides when to render UI and which catalog components to use.
  a2ui: { injectA2UITool: true },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
