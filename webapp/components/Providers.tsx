"use client";

import { CopilotKitProvider } from "@copilotkit/react-core/v2";
import { footballCatalog } from "./A2uiCatalog";

// Passing the catalog via `a2ui={{ catalog }}` does two things:
//  1. Registers our declarative catalog (basic primitives + Recharts Chart)
//     with the built-in A2UI renderer, which activates automatically when the
//     runtime reports a2ui is configured.
//  2. Sends the catalog's component schemas to the agent as context
//     (includeSchema defaults to true), so in dynamic mode the LLM knows which
//     components/props it can use when calling render_a2ui.
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <CopilotKitProvider
      runtimeUrl="/api/copilotkit"
      a2ui={{ catalog: footballCatalog }}
    >
      {children}
    </CopilotKitProvider>
  );
}
