import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { LotteryType } from "@/types/draws"

export function LotterySwitcher({
  value,
  onChange,
}: {
  value: LotteryType
  onChange: (v: LotteryType) => void
}) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as LotteryType)}>
      <TabsList>
        <TabsTrigger value="ssq">双色球</TabsTrigger>
        <TabsTrigger value="dlt">大乐透</TabsTrigger>
      </TabsList>
    </Tabs>
  )
}
