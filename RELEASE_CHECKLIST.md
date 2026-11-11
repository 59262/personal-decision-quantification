# 开源发布清单

## 数据与凭证

- [ ] 已删除或移出真实日记、健康记录、决策记录、状态快照和财务数据
- [ ] 已删除或移出 Apple Health 导出、SQLite 数据库和生成报告
- [ ] 已删除或移出历史恢复包、旧版本快照和个人办公文件
- [ ] 已删除密钥和凭证，并在必要时完成撤销/轮换
- [ ] 已检查 Git 历史；当前顶层无 Git 历史，需在干净副本重新初始化

## 发布材料

- [x] 已准备 `README.md`
- [x] 已准备 `LICENSE.md` 待确认说明
- [x] 已准备 `.gitignore`
- [x] 已准备 `.env.example`
- [x] 已准备 `CONTRIBUTING.md`
- [x] 已准备 `SECURITY.md`
- [x] 已准备 `docs/`
- [x] 已准备虚构示例数据和演示流程
- [x] 已准备 `SECURITY_AUDIT.md`
- [x] 已准备 public-release/ 框架与逻辑暂存目录

## 技术验证

- [ ] 已完成 Python 构建或测试
- [ ] 已完成 PowerShell 语法检查和合成数据运行
- [ ] 已完成 Skill 文件结构检查
- [ ] 已完成示例流程检查
- [ ] 已完成 `git diff --cached` 和 `git status` 审阅
- [ ] 已完成第三方许可证与素材授权核对
- [ ] 已完成在线漏洞数据库核验

## 作者确认

- [ ] 已确认公开范围只包含代码、文档、Skill、测试夹具和虚构示例
- [ ] 已确认 GitHub 仓库名称
- [ ] 已确认许可证（候选：MIT、Apache-2.0，或其他兼容方案）
- [ ] 已确认是否发布 GitHub Release
- [ ] 已确认健康层 `Proprietary` 声明是否改为与项目一致的许可证

## 上传前命令（仅供手动执行，不由本审计执行）

```text
git status
git add .
git diff --cached
git commit -m "Prepare project for open-source release"
git branch -M main
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

