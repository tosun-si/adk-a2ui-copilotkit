"use client";

import { CopilotChat } from "@copilotkit/react-core/v2";
import { Header } from "@/components/Header";

export default function Home() {
  return (
    <div className="flex flex-col h-screen">
      <Header />
      <div className="flex-1 overflow-hidden">
        <CopilotChat
          className="h-full"
          labels={{
            chatInputPlaceholder:
              "Ex. : Qui sont les 5 meilleurs buteurs de France ?",
          }}
        />
      </div>
    </div>
  );
}
