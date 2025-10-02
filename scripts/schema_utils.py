#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库结构工具模块
从JSON配置生成CREATE TABLE语句和其他数据库操作
"""

import json
from pathlib import Path
from typing import Dict, Any, List


class SchemaUtils:
    """数据库结构工具类从JSON配置读取并生成SQL语句"""


    def __init__(self, schema_file: str = None):
        """
        初始化工具类
        Args:
            schema_file (str): JSON配置文件路径如果为None则使用默认路径
        """
        if schema_file is None:
            schema_file = Path(__file__).parent / 'database_schema.json'
        self.schema = self._load_schema(schema_file)


    def _load_schema(self, schema_file: str) -> Dict[str, Any]:
        """
        从JSON文件加载数据库结构配置
        Args:
            schema_file (str): JSON文件路径
        Returns:
            Dict[str, Any]: 数据库结构配置
        """
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load schema file {schema_file}: {e}")


    def generate_create_table_sql(self, table_name: str) -> str:
        """
        从JSON配置生成CREATE TABLE语句
        Args:
            table_name (str): 表名
        Returns:
            str: CREATE TABLE SQL语句
        """
        if table_name not in self.schema['tables']:
            raise ValueError(f"Table {table_name} not found in schema")
        table_def = self.schema['tables'][table_name]
        # 生成列定义
        column_defs = []
        for col in table_def['columns']:
            col_def = f"{col['name']} {col['type']}"
            if col['constraint']:
                col_def += f" {col['constraint']}"
            column_defs.append(col_def)
        # 添加外键约束如果存在
        if 'foreign_keys' in table_def:
            for fk in table_def['foreign_keys']:
                fk_def = f"FOREIGN KEY ({fk['column']}) REFERENCES {fk['references']}"
                column_defs.append(fk_def)
        # 组合完整的SQL语句
        columns_sql = ',\n                '.join(column_defs)
        create_sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
                {columns_sql}
            )"""
        return create_sql


    def generate_all_create_table_sql(self) -> Dict[str, str]:
        """
        生成所有表的CREATE TABLE语句
        Returns:
            Dict[str, str]: 表名 -> CREATE TABLE SQL
        """
        result = {}
        for table_name in self.schema['tables'].keys():
            result[table_name] = self.generate_create_table_sql(table_name)
        return result


    def get_table_columns(self, table_name: str) -> List[str]:
        """
        获取表的所有列名
        Args:
            table_name (str): 表名
        Returns:
            List[str]: 列名列表
        """
        if table_name not in self.schema['tables']:
            raise ValueError(f"Table {table_name} not found in schema")
        return [col['name'] for col in self.schema['tables'][table_name]['columns']]


    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表的索引定义
        Args:
            table_name (str): 表名
        Returns:
            List[Dict[str, Any]]: 索引定义列表
        """
        if table_name not in self.schema['tables']:
            raise ValueError(f"Table {table_name} not found in schema")
        return self.schema['tables'][table_name].get('indexes', [])


    def generate_create_indexes_sql(self, table_name: str) -> List[str]:
        """
        生成表的CREATE INDEX语句
        Args:
            table_name (str): 表名
        Returns:
            List[str]: CREATE INDEX SQL语句列表
        """
        indexes = self.get_table_indexes(table_name)
        sql_statements = []
        for index in indexes:
            index_name = index['name']
            columns = ', '.join(index['columns'])
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})"
            sql_statements.append(sql)
        return sql_statements


    def get_all_table_names(self) -> List[str]:
        """
        获取所有表名
        Returns:
            List[str]: 表名列表
        """
        return list(self.schema['tables'].keys())


    def get_schema_version(self) -> str:
        """
        获取结构版本号
        Returns:
            str: 版本号
        """
        return self.schema.get('version', 'unknown')


def main():
    """主函数示例使用"""
    print("📋 Database Schema Utils")
    print("=" * 50)
    print("该工具从JSON配置生成CREATE TABLE语句")
    print("\n示例用法:")
    print("  from scripts.schema_utils import SchemaUtils")
    print("")
    print("  utils = SchemaUtils()")
    print("  # 生成单个表的CREATE TABLE语句")
    print("  sql = utils.generate_create_table_sql('hbpr_full_records')")
    print("  print(sql)")
    print("")
    print("  # 生成所有表的CREATE TABLE语句")
    print("  all_sql = utils.generate_all_create_table_sql()")
    print("  for table, sql in all_sql.items():")
    print("      print(f'{table}:\\n{sql}\\n')")
    print("\n" + "=" * 50)
    # 演示实际生成
    try:
        utils = SchemaUtils()
        print(f"\n当前数据库结构版本: {utils.get_schema_version()}")
        print(f"\n包含的表: {', '.join(utils.get_all_table_names())}")
        print("\n示例 - flight_info表的CREATE语句:")
        print(utils.generate_create_table_sql('flight_info'))
    except Exception as e:
        print(f"\n错误: {e}")


if __name__ == "__main__":
    main()

