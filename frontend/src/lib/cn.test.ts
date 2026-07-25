import { describe, expect, it } from "vitest";
import { cn } from "@/lib/cn";

describe("cn", () => {
  it("joins class names", () => {
    expect(cn("a", false && "b", "c")).toBe("a c");
  });
});
