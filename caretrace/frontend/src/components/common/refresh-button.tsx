"use client";

import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function RefreshButton({ keys }: { keys: string[][] }) {
  const queryClient = useQueryClient();
  const fetching = useIsFetching() > 0;

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => {
        for (const key of keys) {
          void queryClient.invalidateQueries({ queryKey: key });
        }
      }}
      disabled={fetching}
    >
      <RotateCw className={cn("h-4 w-4", fetching && "animate-spin")} />
      Refresh
    </Button>
  );
}
