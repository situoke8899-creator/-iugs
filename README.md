# QuantLab Pro — Vercel 网页模拟版
**这是针对 Vercel 的独立轻量网页版本，不是原 Streamlit + SQLite + 后台 Worker 的完整迁移。**
- 公开 DexScreener 新代币发现、交易池报价；BNB Chain、Ethereum 的 GoPlus 初筛。
- Solana 风险检查未接入，始终显示不支持。
- 本机浏览器虚拟资金模拟买卖（localStorage），数据不跨设备，不是可验证成交回测。
- **不支持** 24 小时挂机、完整自动策略、真实钱包交易、完整自动跟单、套利执行、训练型 AI。
- 不收集、不输入助记词或私钥。

## Vercel 部署
1. 在 GitHub **新建独立仓库**（建议 `quantlab-vercel`），不要覆盖原 Render 仓库。
2. 解压此 ZIP，把 `api/`、`public/`、`requirements.txt`、`vercel.json` 上传到仓库**根目录**。
3. Vercel → Add New → Project → Import 仓库。
4. Framework Preset: Other；Root Directory: `./`；不要手动填 Build Command、Output Directory。
5. 点击 Deploy，打开 Vercel 分配的网址。此公开预览没有登录权限，任何知道网址的人都可使用自己的浏览器模拟交易。
6. Vercel Serverless 函数是按请求执行，不能长期后台挂机。若要自动挂机和跨设备数据库，必须另接常驻服务 + 持久数据库（例如 Render/VPS），并实现账户权限。
