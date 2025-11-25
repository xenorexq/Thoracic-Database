# 代码审查 - 潜在Bug分析报告

**审查日期：** 2025年11月25日  
**审查范围：** 全部代码文件  
**严重级别：** 🔴 高 / 🟡 中 / 🟢 低

---

## 🔴 严重问题（需要立即修复）

### Bug #1: main.py 导入功能中使用 sqlite3.Row.get()

**位置：** `main.py` 第585行

**代码：**
```python
event_details = evrow.get("event_details", "")
```

**问题：**
- 在导入功能中使用了 `sqlite3.Row.get()`
- 与patient_tab.py中的问题相同，打包后可能失败

**影响：**
- 导入FollowUpEvent时可能失败
- 打包后的exe环境可能出错

**修复优先级：** 🔴 高

---

### Bug #2: 除零错误风险（多处）

**位置 1：** `main.py` 第500行
```python
progress_val = (i / total_pats) * 100
```

**位置 2：** `export/parallel.py` 第33行
```python
progress = (self.completed_tasks / self.total_tasks) * 100
```

**位置 3：** `export/excel.py` 第254、336行
```python
write_progress_step = 30.0 / len(tables)
```

**问题：**
- 如果 `total_pats`, `total_tasks`, 或 `len(tables)` 为 0
- 会导致 `ZeroDivisionError`

**影响：**
- 程序崩溃
- 导入/导出失败

**修复优先级：** 🔴 高

---

### Bug #3: 空异常处理吞掉所有错误

**位置：** `main.py` 多处

```python
except sqlite3.Error: pass  # 第540, 556, 572, 588, 615行
```

**问题：**
- 吞掉了所有SQLite错误
- 导入失败时用户不知道原因
- 无法诊断问题

**影响：**
- 数据可能丢失而用户不知道
- 导入统计不准确

**修复优先级：** 🔴 高

---

### Bug #4: 数据库连接未关闭

**位置：** `main.py` 第617行

```python
except Exception as e:
    self.root.after(0, lambda err=str(e): messagebox.showerror(...))
    continue  # src_conn 可能未关闭
```

**问题：**
- 异常时 `src_conn.close()` 不会被调用
- 文件句柄泄漏

**影响：**
- 资源泄漏
- 可能导致"数据库被锁定"

**修复优先级：** 🔴 高

---

## 🟡 中等问题（建议修复）

### Bug #5: 类型转换可能失败

**位置：** `ui/surgery_tab.py` 第389-390行

```python
"lesion_count": int(self.lesion_count_var.get()) if self.lesion_count_var.get() else None,
"main_lesion_size_cm": float(self.main_size_var.get()) if self.main_size_var.get() else None,
```

**问题：**
- 如果用户输入非数字（如"无"、"N/A"），`int()` 或 `float()` 会抛出异常
- 没有try-catch保护

**影响：**
- 保存失败且错误提示不友好

**修复优先级：** 🟡 中

---

### Bug #6: 字典键可能不存在

**位置：** `main.py` 第583-584行

```python
event_date = evrow["event_date"]  # 直接访问，可能KeyError
event_type = evrow["event_type"]
```

**问题：**
- 如果源数据库表结构不同，字段可能不存在
- 会抛出 KeyError

**影响：**
- 导入旧版本数据库时可能失败

**修复优先级：** 🟡 中

---

### Bug #7: 进度窗口重复创建

**位置：** `main.py` 第380-395行

```python
def show_progress(self, show: bool):
    if show:
        if not hasattr(self, 'progress_window') or not self.progress_window.winfo_exists():
            self.progress_window = tk.Toplevel(...)
```

**问题：**
- 如果快速连续调用，可能创建多个窗口
- 没有线程锁保护

**影响：**
- 内存泄漏
- 界面混乱

**修复优先级：** 🟡 中

---

### Bug #8: SQLite连接的线程安全性

**位置：** `export/parallel.py` 全文

**问题：**
- 多个线程同时使用同一个 `db.conn`
- SQLite 默认不支持多线程写入
- 虽然只是读取，但仍有风险

**影响：**
- 可能的数据库锁定
- 查询失败

**修复优先级：** 🟡 中

---

## 🟢 小问题（可以优化）

### Bug #9: 文件路径处理

**位置：** 多处使用 `Path()` 和字符串拼接

**问题：**
- 混合使用 Path 对象和字符串
- Windows路径中的反斜杠可能有问题

**影响：**
- 跨平台兼容性问题

**修复优先级：** 🟢 低

---

### Bug #10: 日志输出使用print

**位置：** `export/parallel.py` 等多处

```python
print(f"Error fetching data from table {table}: {e}")
```

**问题：**
- 使用 `print` 而非日志系统
- 打包后的exe可能看不到输出

**影响：**
- 调试困难

**修复优先级：** 🟢 低

---

### Bug #11: 魔法数字

**位置：** `main.py` 第499, 520行

```python
if i % 50 == 0:  # 魔法数字50
chunk_size = 500  # 魔法数字500
```

**问题：**
- 硬编码的数字缺少注释
- 不易调整

**影响：**
- 代码可维护性

**修复优先级：** 🟢 低

---

## 📋 问题汇总

| Bug ID | 描述 | 严重级别 | 位置 |
|--------|------|---------|------|
| #1 | sqlite3.Row.get() 兼容性 | 🔴 高 | main.py:585 |
| #2 | 除零错误风险 | 🔴 高 | main.py:500, parallel.py:33 |
| #3 | 空异常处理 | 🔴 高 | main.py 多处 |
| #4 | 连接未关闭 | 🔴 高 | main.py:617 |
| #5 | 类型转换失败 | 🟡 中 | surgery_tab.py:389-390 |
| #6 | 字典键不存在 | 🟡 中 | main.py:583-584 |
| #7 | 进度窗口重复 | 🟡 中 | main.py:380 |
| #8 | 线程安全性 | 🟡 中 | parallel.py 全文 |
| #9 | 路径处理 | 🟢 低 | 多处 |
| #10 | 日志使用print | 🟢 低 | parallel.py 多处 |
| #11 | 魔法数字 | 🟢 低 | main.py 多处 |

---

## 🔧 建议的修复顺序

### 第一优先级（立即修复）

1. **修复 Bug #1** - sqlite3.Row.get() 兼容性
2. **修复 Bug #2** - 除零错误
3. **修复 Bug #3** - 改进异常处理
4. **修复 Bug #4** - 确保连接关闭

### 第二优先级（本周修复）

5. **修复 Bug #5** - 类型转换保护
6. **修复 Bug #6** - 字典访问安全
7. **修复 Bug #7** - 窗口管理
8. **修复 Bug #8** - 线程安全

### 第三优先级（后续优化）

9. **优化 Bug #9** - 路径处理统一
10. **优化 Bug #10** - 日志系统统一
11. **优化 Bug #11** - 常量定义

---

## 📊 风险评估

### 高风险场景

1. **导入大量数据时**
   - Bug #2, #3, #4 可能导致崩溃或数据丢失
   
2. **打包后使用**
   - Bug #1 会导致导入失败
   
3. **并发操作时**
   - Bug #8 可能导致数据库锁定

### 低风险场景

- 小数据量操作
- 单用户环境
- 开发环境（Python直接运行）

---

## ✅ 已经做得很好的地方

1. ✅ 使用参数化查询（防止SQL注入）
2. ✅ 外键约束启用
3. ✅ 事务管理（大部分地方）
4. ✅ 错误提示（最近改进）
5. ✅ 数据验证（patient_tab）
6. ✅ ID冲突防护（设计层面）

---

## 🎯 修复建议

每个Bug都会在后续消息中逐一修复，确保代码质量。

---

**审查完成时间：** 2025年11月25日  
**审查者：** AI代码审查工具  
**审查版本：** v3.6.2-rc

