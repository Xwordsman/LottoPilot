import { useMutation } from "@tanstack/react-query"
import { FormEvent, useState } from "react"
import { useNavigate } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { apiRequest, ApiError } from "@/lib/api"
import { useAuthStore } from "@/lib/auth-store"
import type { LoginData } from "@/types/api"

export function SetupPage() {
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)
  const setInitialized = useAuthStore((s) => s.setInitialized)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [displayName, setDisplayName] = useState("管理员")
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest<LoginData>("/setup", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          display_name: displayName,
        }),
      })
      return res.data!
    },
    onSuccess: (data) => {
      setUser(data.user)
      setInitialized(true)
      navigate("/", { replace: true })
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) setError(err.message)
      else setError("初始化失败")
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    mutation.mutate()
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>初始化 LottoPilot</CardTitle>
          <CardDescription>首次启动需要创建管理员账号。完成后即可登录使用。</CardDescription>
        </CardHeader>
        <form onSubmit={onSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="displayName">显示名称</Label>
              <Input
                id="displayName"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">管理员邮箱</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码（至少 8 位）</Label>
              <Input
                id="password"
                type="password"
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error ? (
              <Alert variant="destructive">
                <AlertTitle>初始化失败</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
          <CardFooter>
            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? "提交中..." : "完成初始化"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
