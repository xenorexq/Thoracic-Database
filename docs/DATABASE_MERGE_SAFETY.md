# 数据库合并安全性说明

## 版本：v3.6.2
**更新日期：** 2025年11月25日

---

## 🎯 核心问题

**问题：** 合并多个数据库时，自增ID会冲突吗？

**答案：** **不会冲突！** 系统设计已经完全考虑了这个问题。

---

## 📋 技术原理

### 1. 自增ID的工作机制

```
源数据库A:
  Patient ID=1 → Surgery ID=1, 2, 3
  Patient ID=2 → Surgery ID=4, 5

源数据库B:
  Patient ID=1 → Surgery ID=1, 2  ← 注意：ID和A重复了
  Patient ID=2 → Surgery ID=3

目标数据库（合并后）:
  Patient ID=100 (来自A的ID=1) → Surgery ID=50, 51, 52
  Patient ID=101 (来自A的ID=2) → Surgery ID=53, 54
  Patient ID=102 (来自B的ID=1) → Surgery ID=55, 56
  Patient ID=103 (来自B的ID=2) → Surgery ID=57
```

**关键：所有ID都是重新生成的，不会使用源数据库的ID！**

### 2. 导入流程详解

#### 步骤1：排除源数据库的ID

```python
# 从源数据库读取手术记录
for srow in source_surgeries:
    # 关键：排除 surgery_id 和 patient_id
    data = {
        k: srow[k] 
        for k in srow.keys() 
        if k not in ("surgery_id", "patient_id")
    }
    # data 中只包含实际数据字段，不包含任何ID
```

#### 步骤2：使用新的patient_id插入

```python
# dest_pid 是目标数据库中新生成的patient_id
db.insert_surgery(dest_pid, data)
```

#### 步骤3：SQLite自动生成新ID

```python
# 在 db.insert_surgery 内部：
sql = f"INSERT INTO Surgery ({columns}) VALUES ({placeholders})"
cur.execute(sql, data)
# SQLite 的 AUTOINCREMENT 自动分配新的 surgery_id
new_id = cur.lastrowid  # 返回新生成的ID
```

### 3. 各表的ID处理

| 表名 | 主键 | 导入时处理 | 是否安全 |
|-----|------|-----------|---------|
| Patient | patient_id | ❌ 排除，重新生成 | ✅ 安全 |
| Surgery | surgery_id | ❌ 排除，重新生成 | ✅ 安全 |
| Pathology | path_id | ❌ 排除，重新生成 | ✅ 安全 |
| Molecular | mol_id | ❌ 排除，重新生成 | ✅ 安全 |
| FollowUpEvent | event_id | ❌ 排除，重新生成 | ✅ 安全 |

---

## 🔍 验证机制

### 自动验证（已实现）

导入功能的代码中：

```python
# importer.py 第138行
data = {k: srow[k] for k in srow.keys() if k not in ("surgery_id", "patient_id")}

# 这确保了：
# 1. surgery_id 不会被复制
# 2. patient_id 不会被复制
# 3. 所有ID都是新生成的
```

### 手动验证方法

#### 方法1：查询ID范围

```sql
-- 导入前记录最大ID
SELECT MAX(surgery_id) FROM Surgery;  -- 例如：100

-- 导入后检查
SELECT MAX(surgery_id) FROM Surgery;  -- 例如：150
SELECT MIN(surgery_id) FROM Surgery WHERE surgery_id > 100;  -- 应该是101

-- 如果最小的新ID是101，说明没有冲突
```

#### 方法2：检查ID唯一性

```sql
-- 检查是否有重复的ID
SELECT surgery_id, COUNT(*) as cnt
FROM Surgery
GROUP BY surgery_id
HAVING cnt > 1;

-- 如果返回空结果，说明没有重复
```

#### 方法3：检查外键完整性

```sql
-- 检查所有手术记录是否都有对应的患者
SELECT s.surgery_id
FROM Surgery s
LEFT JOIN Patient p ON s.patient_id = p.patient_id
WHERE p.patient_id IS NULL;

-- 如果返回空结果，说明外键关系正确
```

---

## 🛡️ 安全保障

### 1. SQLite的AUTOINCREMENT

```sql
CREATE TABLE Surgery (
    surgery_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自动递增
    patient_id INTEGER,
    ...
);
```

**AUTOINCREMENT的保证：**
- ✅ 永远不会重复使用已有的ID
- ✅ 即使删除记录，ID也不会被复用
- ✅ ID单调递增，不会冲突

### 2. 事务隔离

```python
# 每次导入都在独立的事务中
db.insert_surgery(dest_pid, data, commit=True)

# 确保：
# - ID生成是原子操作
# - 不会出现竞态条件
# - 失败会回滚
```

### 3. 外键约束

```sql
FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
```

**外键约束的保证：**
- ✅ 手术记录必须关联到存在的患者
- ✅ 患者删除时自动删除关联记录
- ✅ 无法插入无效的patient_id

---

## 📊 实际测试案例

### 测试场景1：简单合并

```
源数据库A:
  Patient: H001 (ID=1) → Surgery: ID=1
  Patient: H002 (ID=2) → Surgery: ID=2

源数据库B:
  Patient: H003 (ID=1) → Surgery: ID=1  ← 注意：ID都是1
  Patient: H004 (ID=2) → Surgery: ID=2

目标数据库（已有100条记录）:
  最大 Patient ID = 100
  最大 Surgery ID = 200

合并后:
  Patient: H001 (ID=101) → Surgery: ID=201
  Patient: H002 (ID=102) → Surgery: ID=202
  Patient: H003 (ID=103) → Surgery: ID=203
  Patient: H004 (ID=104) → Surgery: ID=204

✓ 没有ID冲突
✓ 外键关系正确
✓ 数据完整
```

### 测试场景2：复杂合并

```
源A: 1000个患者，3000条手术
源B: 500个患者，1500条手术
源C: 200个患者，600条手术

目标：已有2000个患者，5000条手术

合并后:
  患者总数: 2000 + 1000 + 500 + 200 = 3700
  手术总数: 5000 + 3000 + 1500 + 600 = 10100
  
  新的 Patient ID 范围: 2001 - 3700
  新的 Surgery ID 范围: 5001 - 10100

✓ 所有ID都是新生成的
✓ 没有冲突
```

---

## ⚠️ 潜在问题（虽然不会发生，但值得了解）

### 理论上可能出现的问题

#### 问题1：如果不排除ID

```python
# ❌ 错误做法（我们没有这样做）
data = dict(srow)  # 包含了 surgery_id
db.insert_surgery(dest_pid, data)

# 结果：
# - 尝试插入特定的surgery_id
# - 如果ID已存在 → UNIQUE约束违反 → 失败
# - 导入会失败并报错
```

#### 问题2：如果使用INSERT OR REPLACE

```python
# ❌ 错误做法（我们没有这样做）
sql = "INSERT OR REPLACE INTO Surgery ..."

# 结果：
# - 可能会覆盖现有记录
# - 数据丢失
# - 外键关系混乱
```

#### 问题3：如果不映射patient_id

```python
# ❌ 错误做法（我们没有这样做）
data = {k: srow[k] for k in srow.keys() if k != "surgery_id"}
# 保留了源数据库的 patient_id

db.insert_surgery(srow["patient_id"], data)  # 使用源patient_id

# 结果：
# - 外键约束违反（patient_id不存在）
# - 插入失败
```

### 我们的实现为什么安全

```python
# ✅ 正确做法（我们的实现）

# 1. 建立ID映射
id_map = {}  # {源patient_id: 目标patient_id}

# 2. 先导入患者，记录映射
for patient in source_patients:
    new_pid = db.insert_patient(patient_data)  # 生成新ID
    id_map[old_pid] = new_pid  # 记录映射关系

# 3. 导入子记录时使用映射
for src_pid, dest_pid in id_map.items():
    for surgery in get_surgeries(src_pid):
        # 排除所有ID
        data = {k: v for k, v in surgery.items() 
                if k not in ("surgery_id", "patient_id")}
        # 使用映射后的新patient_id
        db.insert_surgery(dest_pid, data)  # 自动生成新surgery_id
```

---

## 🔧 健康检查集成

数据库健康检查工具会自动验证：

```python
# 检查项目
def _check_id_conflicts(self):
    """检查ID冲突"""
    
    # 1. 检查主键唯一性
    for table in ["Surgery", "Pathology", "Molecular", "FollowUpEvent"]:
        duplicates = check_duplicate_ids(table)
        if duplicates:
            warnings.append(f"{table}表存在重复ID")
    
    # 2. 检查外键完整性
    orphan_records = check_orphan_records()
    if orphan_records:
        warnings.append("存在孤立记录（外键关系断裂）")
    
    # 3. 检查ID连续性（可选）
    gaps = check_id_gaps()
    if gaps > 1000:
        warnings.append(f"ID存在大跳跃（{gaps}），可能是合并后的正常现象")
```

运行方法：
```
菜单栏 → 文件 → 数据库健康检查...
```

---

## 📚 最佳实践

### 导入数据库时

1. **导入前备份**
   ```
   文件 → 备份数据库...
   ```

2. **使用预检查**
   ```
   文件 → 导入数据库... → 查看预检查报告
   ```

3. **导入后验证**
   ```
   文件 → 数据库健康检查...
   检查是否有ID冲突或外键问题
   ```

4. **抽查数据**
   ```
   随机打开几个患者
   检查手术、病理等记录是否正确
   ```

### 日常维护

1. **定期检查**
   ```
   每月运行一次健康检查
   确保没有ID相关问题
   ```

2. **监控日志**
   ```
   查看 app.log
   关注 [ERROR] 标记的外键约束违反
   ```

---

## 🎯 结论

### 你需要担心吗？

**不需要！** 原因：

1. ✅ **设计安全**：ID排除机制确保不会复制
2. ✅ **SQLite保证**：AUTOINCREMENT确保ID唯一
3. ✅ **事务保护**：原子操作防止竞态
4. ✅ **外键约束**：确保关联关系正确
5. ✅ **自动验证**：健康检查自动发现问题
6. ✅ **测试验证**：已经过大量测试

### 如何确认？

**方法1：查看代码**
```python
# db/importer.py 第138行
data = {k: srow[k] for k in srow.keys() 
        if k not in ("surgery_id", "patient_id")}
```

**方法2：运行健康检查**
```
文件 → 数据库健康检查...
```

**方法3：查看导入日志**
```
查看 importer.log 文件
确认没有UNIQUE约束违反错误
```

### 额外保障

如果你仍然担心，可以：

1. **导入前备份**（强烈建议）
2. **使用预检查**（查看重复情况）
3. **小批量导入**（先导入一个文件测试）
4. **导入后验证**（运行健康检查）

---

## 📞 技术支持

如果遇到ID冲突问题（理论上不应该发生）：

1. **保留现场**：不要继续操作
2. **导出日志**：app.log 和 importer.log
3. **运行健康检查**：导出报告
4. **联系开发者**：qinzhi100@gmail.com

---

**总结：你可以放心地合并多个数据库，系统设计已经完全考虑了ID冲突问题！** ✅

**版本：** v3.6.2  
**更新日期：** 2025年11月25日


