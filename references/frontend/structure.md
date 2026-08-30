# 前端项目结构规范（React + TypeScript + Vite）

> **Pre-Check（加载前确认）：** 几个页面/路由？状态管理用 Zustand 还是 Context？UI 组件库选 Ant Design 还是 Tailwind？是否已有后端 API 文档？
>
> 本文件代码均为参考模板（Reference Template），可结合实际业务调整实现，但须保证可编译运行、不引入 bug；不确定时遵循模板。
>
> **Deliverable（读完必须产出）：** 完整前端目录 + request 封装/router 配置/一个完整页面样例。

## 目录结构

```
frontend/                          # 或 apps/web/（Monorepo 模式）
├── public/                        # 不参与构建的静态资源（直接复制到 dist）
│   └── favicon.ico
├── src/                           # 源代码（所有业务代码都在这里）
│   ├── assets/                    # 图片、字体、图标（参与构建，会被压缩优化）
│   │   └── logo.png
│   ├── components/                # 可复用 UI 零件（按钮、弹窗、表格、通用卡片）
│   │   ├── Table/
│   │   ├── Modal/
│   │   └── Form/
│   ├── layouts/                   # 页面布局（侧边栏+顶部栏的整体框架）
│   │   ├── BasicLayout/          # 登录后的主布局（侧边栏+顶部栏+内容区）
│   │   └── BlankLayout/          # 空白布局（登录页、404页用）
│   ├── pages/                     # 业务页面（学生列表页、个人中心页）
│   │   ├── Login/
│   │   │   └── index.tsx
│   │   ├── StudentList/
│   │   │   └── index.tsx
│   │   └── StudentEdit/
│   │       └── index.tsx
│   ├── hooks/                     # 可复用的业务逻辑（自定义 Hook）
│   │   ├── useStudent.ts         # 学生相关逻辑封装
│   │   ├── useDebounce.ts        # 防抖
│   │   └── usePagination.ts      # 分页逻辑
│   ├── stores/                    # 全局状态（登录用户、主题色、权限）
│   │   ├── useUserStore.ts       # 用户信息 store
│   │   ├── useAppStore.ts        # 应用全局 store（主题、侧边栏折叠）
│   │   └── index.ts
│   ├── services/                  # 与后端通信的代码（API 请求封装）
│   │   ├── request.ts             # Axios 实例 + 拦截器
│   │   ├── student.ts             # 学生相关接口
│   │   └── auth.ts                # 登录认证接口
│   ├── router/                    # 路由配置（哪个 URL 显示哪个页面）
│   │   └── index.tsx
│   ├── types/                     # TypeScript 类型定义
│   │   ├── api.ts                 # API 响应类型
│   │   ├── student.ts             # 学生相关类型
│   │   └── user.ts                # 用户相关类型
│   ├── utils/                     # 纯工具函数（无业务逻辑）
│   │   ├── auth.ts                # token 存取
│   │   ├── format.ts              # 日期格式化
│   │   └── download.ts            # 文件下载
│   ├── constants/                 # 常量（固定不变的值）
│   │   ├── index.ts               # 通用常量
│   │   └── dict.ts                # 字典常量（性别、状态等枚举）
│   ├── App.tsx                    # 根组件（总控台）
│   ├── main.tsx                   # 入口文件（开机按钮）
│   └── vite-env.d.ts              # Vite 类型声明
├── .env.development               # 开发环境变量
├── .env.production                # 生产环境变量
├── eslint.config.js               # 代码规范检查配置
├── .prettierrc                    # Prettier 配置
├── index.html                     # 浏览器加载的 HTML 外壳
├── package.json                   # 项目身份证 + 依赖 + 脚本
├── tsconfig.json                  # TypeScript 配置
├── tsconfig.node.json
└── vite.config.ts                 # Vite 配置（路径别名、代理）
```

## 各目录职责说明

| 目录 | 职责 | 放什么 | 不放什么 |
|------|------|--------|---------|
| `components/` | 通用 UI 零件 | 按钮、表格、弹窗、表单控件等多页面复用的组件 | 只在一个页面用的组件（放页面目录内） |
| `layouts/` | 页面整体框架 | 带侧边栏+顶部栏的主布局、空白布局 | 具体业务页面内容 |
| `pages/` | 业务页面 | 按路由划分的页面组件，每个页面对应一个 URL | 通用组件（提取到 components/） |
| `hooks/` | 可复用逻辑 | 自定义 Hook，封装有状态的业务逻辑 | 纯函数（放 utils/）、无复用价值的逻辑（写在组件内） |
| `stores/` | 全局状态 | 跨组件共享的状态（用户信息、主题、权限） | 组件内部状态（用 useState） |
| `services/` | 后端通信 | Axios 封装、各业务模块的 API 调用函数 | 业务逻辑（放 hooks/ 或页面内） |
| `router/` | 路由配置 | 路由表、路由守卫（权限控制） | 页面组件 |
| `types/` | 类型定义 | TS interface、type，API 响应类型、业务实体类型 | 运行时代码 |
| `utils/` | 纯工具函数 | 无副作用、无业务依赖的函数（日期格式化、防抖） | 有业务逻辑的函数（放 hooks/） |
| `constants/` | 常量 | 固定不变的值（枚举字典、默认分页大小、缓存 key） | 会变化的配置（用环境变量） |
| `assets/` | 静态资源 | 图片、字体、SVG 图标（会被构建压缩） | 不需要构建处理的文件（放 public/） |

## 关键配置

### vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
```

### tsconfig.json（路径别名）

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

### Axios 封装（src/services/request.ts）

```typescript
import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 请求拦截器：自动加 token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理错误
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default request
```

### 接口定义示例（src/services/student.ts）

```typescript
import request from './request'
import type { Student, PageResult, PageParams } from '@/types/student'

export const getStudentList = (params: PageParams) =>
  request.get<unknown, PageResult<Student>>('/students', { params })

export const getStudent = (id: number) =>
  request.get<unknown, Student>(`/students/${id}`)

export const createStudent = (data: Omit<Student, 'id'>) =>
  request.post<unknown, Student>('/students', data)

export const updateStudent = (id: number, data: Partial<Student>) =>
  request.put<unknown, Student>(`/students/${id}`, data)

export const deleteStudent = (id: number) =>
  request.delete<unknown, void>(`/students/${id}`)
```

### 为什么必须通过 services/ 调后端，不能在页面里直接写 axios？

```
页面（pages/）
  ↓ 调用
studentService.getStudents()        ← services/ 层
  ↓ HTTP GET /api/students
Spring Boot 后端
  ↓ 返回 JSON
页面更新
```

**解耦理由：**
- 页面只负责"显示"，services/ 只负责"通信"，职责分离
- 后端地址变更、鉴权方式变更、错误处理变更、加重试策略，只改 services/ 一个地方，不用翻遍所有页面
- 接口函数可以在多个页面、多个 Hook 中复用
- 统一在 request.ts 拦截器里加 token、处理 401 跳转、统一 loading

**禁止在 pages/components 里直接 `import axios` 发请求，必须走 services/ 层。**

> ⚠️ **命名混淆提醒**：前端的 `services/` 是调后端接口的 HTTP 通信层；后端的 `service/` 是业务逻辑层（判断规则、组合数据）。两者名字相似但完全不是一回事。前端 services/ 发的是 HTTP 请求，后端 service/ 做的是业务判断。

### Vite 在开发、构建、生产三个阶段分别干什么

| 阶段 | Vite 做什么 | 结果 |
|------|-----------|------|
| **开发**（`npm run dev`） | 启动本地开发服务器、热更新（HMR，改代码页面秒刷新）、模块化按需加载 | localhost:5173 开发地址 |
| **构建**（`npm run build`） | 编译 TS、打包 JS/CSS、压缩、代码分割、生成哈希文件名 | 输出到 `dist/` 目录 |
| **生产** | Vite 不再运行，`dist/` 由 Nginx 或 CDN 提供给浏览器 | 用户访问的是静态文件 |

> 生产环境不需要 Node.js 运行时，只需要 Nginx 托管 dist/ 静态文件。

### 全局状态示例（src/stores/useUserStore.ts）

```typescript
import { create } from 'zustand'
import type { User } from '@/types/user'

interface UserState {
  user: User | null
  token: string | null
  setUser: (user: User) => void
  setToken: (token: string) => void
  logout: () => void
}

export const useUserStore = create<UserState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  setUser: (user) => set({ user }),
  setToken: (token) => {
    localStorage.setItem('token', token)
    set({ token })
  },
  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null })
  },
}))
```

### 自定义 Hook 示例（src/hooks/useStudent.ts）

```typescript
import { useState, useEffect } from 'react'
import { getStudentList } from '@/services/student'
import type { Student, PageParams } from '@/types/student'

export function useStudent(params: PageParams) {
  const [list, setList] = useState<Student[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  const fetch = async () => {
    setLoading(true)
    try {
      const res = await getStudentList(params)
      setList(res.content)
      setTotal(res.totalElements)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, [params.page, params.size])

  return { list, total, loading, refresh: fetch }
}
```

### 常量示例（src/constants/dict.ts）

```typescript
// 性别字典
export const GENDER_OPTIONS = [
  { label: '男', value: 1 },
  { label: '女', value: 2 },
] as const

// 学生状态
export const STUDENT_STATUS = {
  ACTIVE: { label: '在读', value: 1, color: 'success' },
  SUSPENDED: { label: '休学', value: 2, color: 'warning' },
  GRADUATED: { label: '已毕业', value: 3, color: 'default' },
} as const

// 分页默认值
export const DEFAULT_PAGE = 1
export const DEFAULT_PAGE_SIZE = 10
export const MAX_PAGE_SIZE = 100
```

## 组件规范

- 函数组件 + Hooks，不用 class 组件
- 组件文件名 PascalCase：`StudentList.tsx`
- 一个文件一个默认导出组件
- 通用组件放 `components/`，页面组件放 `pages/`
- 页面组件内可包含子组件文件夹，但不复用的子组件不提取到 `components/`

## 环境变量

- 变量名必须以 `VITE_` 前缀：`VITE_API_BASE_URL`
- `.env.development`：开发环境
- `.env.production`：生产环境
- 代码中通过 `import.meta.env.VITE_XXX` 读取
