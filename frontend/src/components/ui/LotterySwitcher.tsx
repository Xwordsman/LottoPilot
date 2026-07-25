import { Button } from "@/components/ui/Button";
import type { LotteryType } from "@/types/draws";

export function LotterySwitcher({
  value,
  onChange,
}: {
  value: LotteryType;
  onChange: (next: LotteryType) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {(["ssq", "dlt"] as const).map((key) => (
        <Button
          key={key}
          variant={value === key ? "primary" : "secondary"}
          onClick={() => onChange(key)}
        >
          {key.toUpperCase()}
        </Button>
      ))}
    </div>
  );
}