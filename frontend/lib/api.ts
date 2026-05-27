/**
 * 统一的 API Base URL 配置
 *
 * 优先级：
 *   1. NEXT_PUBLIC_API_BASE_URL（运行/构建时环境变量）
 *   2. 同源 /api 反向代理（线上部署推荐）
 *   3. 兜底 http://127.0.0.1:8000（本地开发默认端口）
 *
 * 修复历史：原 market/review 页面写死 127.0.0.1:8005，与启动脚本的 8000 端口冲突
 * 导致大盘和复盘页面所有请求 ERR_CONNECTION_REFUSED。
 */
export const API_BASE =
  (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_BASE_URL) ||
  'http://127.0.0.1:8005'
