#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown文档自动聚类脚本

使用无监督机器学习方法对MD文档进行聚类分析：
- 基于TF-IDF和文档结构特征进行特征提取
- 使用K-means聚类算法自动发现文档类别
- 支持自动确定最优聚类数量
- 生成聚类分析报告和可视化结果
"""

import os
import re
import argparse
import shutil
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import seaborn as sns


class MarkdownClusterer:
    """Markdown文档聚类器"""
    
    def __init__(self, n_clusters: Optional[int] = None, max_clusters: int = 10):
        """
        初始化聚类器
        
        Args:
            n_clusters: 指定聚类数量，如果为None则自动确定最优数量
            max_clusters: 自动确定聚类数量时的最大值
        """
        self.n_clusters = n_clusters
        self.max_clusters = max_clusters
        self.tfidf_vectorizer = None
        self.kmeans = None
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=2)
        self.feature_names = []
        self.documents = []
        self.file_paths = []
        self.features_df = None
        self.cluster_labels = None
    
    def extract_structural_features(self, content: str) -> Dict[str, float]:
        """提取文档结构特征"""
        features = {}
        
        # 文档长度
        features['length'] = len(content)
        
        # 行数
        lines = content.split('\n')
        features['line_count'] = len(lines)
        
        # 数学公式特征（LaTeX格式）
        latex_patterns = [
            r'\$\$[^$]+\$\$',  # 块级公式
            r'\$[^$]+\$',     # 行内公式
            r'\\begin\{equation\}',  # equation环境
            r'\\begin\{align\}',     # align环境
            r'\\begin\{matrix\}',    # matrix环境
            r'\\frac\{[^}]+\}\{[^}]+\}',  # 分数
            r'\\sum_\{[^}]*\}',      # 求和
            r'\\int_\{[^}]*\}',      # 积分
            r'\\alpha|\\beta|\\gamma|\\delta',  # 希腊字母
        ]
        
        formula_count = 0
        for pattern in latex_patterns:
            formula_count += len(re.findall(pattern, content, re.IGNORECASE))
        features['formula_density'] = formula_count / max(features['line_count'], 1)
        
        # 表格特征
        table_patterns = [
            r'\|[^\n]*\|',  # Markdown表格
            r'\+[-=]+\+',   # ASCII表格
        ]
        table_count = 0
        for pattern in table_patterns:
            table_count += len(re.findall(pattern, content))
        features['table_density'] = table_count / max(features['line_count'], 1)
        
        # 代码块特征
        code_patterns = [
            r'```[^`]*```',     # 代码块
            r'`[^`]+`',         # 行内代码
            r'    [^\n]+',      # 缩进代码
        ]
        code_count = 0
        for pattern in code_patterns:
            code_count += len(re.findall(pattern, content, re.DOTALL))
        features['code_density'] = code_count / max(features['line_count'], 1)
        
        # 标题检测和结构分析
        heading_features = self._extract_heading_features(content)
        features.update(heading_features)
        
        # 列表特征
        list_patterns = [
            r'^\s*[-*+]\s+',    # 无序列表
            r'^\s*\d+\.\s+',    # 有序列表
        ]
        list_count = 0
        for pattern in list_patterns:
            list_count += len(re.findall(pattern, content, re.MULTILINE))
        features['list_density'] = list_count / max(features['line_count'], 1)
        
        # 链接和引用特征
        link_count = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content))
        citation_count = len(re.findall(r'\[[0-9]+\]|\[\w+\s*\d{4}\]', content))
        features['link_density'] = link_count / max(features['line_count'], 1)
        features['citation_density'] = citation_count / max(features['line_count'], 1)
        
        return features
    
    def _calculate_variance(self, values: List[int]) -> float:
        """计算方差"""
        if not values:
            return 0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _extract_heading_features(self, content: str) -> Dict[str, float]:
        """提取标题检测特征"""
        features = {}
        
        # 提取所有标题
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        headings = re.findall(heading_pattern, content, re.MULTILINE)
        
        if not headings:
            features.update({
                'header_count': 0,
                'max_header_depth': 0,
                'header_variance': 0,
                'heading_text_length': 0,
                'heading_structure_complexity': 0,
                'heading_depth_transitions': 0
            })
            return features
        
        # 基本标题统计
        header_levels = [len(h[0]) for h in headings]
        header_texts = [h[1].strip() for h in headings]
        
        features['header_count'] = len(headings)
        features['max_header_depth'] = max(header_levels)
        features['header_variance'] = self._calculate_variance(header_levels)
        
        # 标题文本长度特征
        heading_text_combined = ' '.join(header_texts)
        features['heading_text_length'] = len(heading_text_combined)
        
        # 目录结构复杂度分析
        features['heading_structure_complexity'] = self._calculate_heading_structure_complexity(header_levels)
        
        # 标题深度变化次数（反映目录结构的跳跃性）
        depth_transitions = 0
        for i in range(1, len(header_levels)):
            if header_levels[i] != header_levels[i-1]:
                depth_transitions += 1
        features['heading_depth_transitions'] = depth_transitions / max(len(header_levels), 1)
        
        return features
    
    def _calculate_heading_structure_complexity(self, header_levels: List[int]) -> float:
        """计算标题结构复杂度"""
        if len(header_levels) <= 1:
            return 0
        
        # 计算层级跳跃的复杂度
        complexity = 0
        for i in range(1, len(header_levels)):
            level_diff = abs(header_levels[i] - header_levels[i-1])
            # 跳跃越大，复杂度越高
            if level_diff > 1:
                complexity += level_diff * 0.5
            elif level_diff == 1:
                complexity += 0.1
        
        # 标准化复杂度
        return complexity / len(header_levels)
    
    def _build_heading_tree(self, headings: List[Tuple[str, str]]) -> Dict:
        """构建标题目录树结构"""
        if not headings:
            return {}
        
        tree = {'children': [], 'level': 0, 'text': 'root'}
        stack = [tree]
        
        for level_str, text in headings:
            level = len(level_str)
            node = {'level': level, 'text': text.strip(), 'children': []}
            
            # 找到合适的父节点
            while len(stack) > 1 and stack[-1]['level'] >= level:
                stack.pop()
            
            # 添加到父节点
            stack[-1]['children'].append(node)
            stack.append(node)
        
        return tree
    
    def _calculate_edit_distance(self, str1: str, str2: str) -> int:
        """计算编辑距离（Levenshtein距离）"""
        if not str1:
            return len(str2)
        if not str2:
            return len(str1)
        
        # 动态规划计算编辑距离
        m, n = len(str1), len(str2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # 初始化
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # 填充DP表
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i-1] == str2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return dp[m][n]
    
    def calculate_heading_similarity(self, content1: str, content2: str) -> Dict[str, float]:
        """计算两个文档的标题相似度"""
        # 提取标题
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        headings1 = re.findall(heading_pattern, content1, re.MULTILINE)
        headings2 = re.findall(heading_pattern, content2, re.MULTILINE)
        
        # 拼接所有标题文本
        text1 = ' '.join([h[1].strip() for h in headings1])
        text2 = ' '.join([h[1].strip() for h in headings2])
        
        # 计算编辑距离相似度（EDS）
        if not text1 and not text2:
            eds = 1.0
        elif not text1 or not text2:
            eds = 0.0
        else:
            edit_dist = self._calculate_edit_distance(text1.lower(), text2.lower())
            max_len = max(len(text1), len(text2))
            eds = 1.0 - (edit_dist / max_len) if max_len > 0 else 1.0
        
        # 构建目录树并计算树编辑距离
        tree1 = self._build_heading_tree(headings1)
        tree2 = self._build_heading_tree(headings2)
        
        # 简化的树结构相似度计算
        tree_similarity = self._calculate_tree_similarity(tree1, tree2)
        
        return {
            'heading_eds': eds,
            'heading_tree_similarity': tree_similarity,
            'heading_count_diff': abs(len(headings1) - len(headings2))
        }
    
    def _calculate_tree_similarity(self, tree1: Dict, tree2: Dict) -> float:
        """计算树结构相似度（简化版树编辑距离）"""
        if not tree1.get('children') and not tree2.get('children'):
            return 1.0
        
        if not tree1.get('children') or not tree2.get('children'):
            return 0.0
        
        children1 = tree1['children']
        children2 = tree2['children']
        
        # 计算子节点的相似度矩阵
        similarities = []
        for child1 in children1:
            row = []
            for child2 in children2:
                # 文本相似度
                text_sim = 1.0 - (self._calculate_edit_distance(
                    child1['text'].lower(), child2['text'].lower()
                ) / max(len(child1['text']), len(child2['text']), 1))
                
                # 层级相似度
                level_sim = 1.0 - abs(child1['level'] - child2['level']) / 6.0
                
                # 递归计算子树相似度
                subtree_sim = self._calculate_tree_similarity(child1, child2)
                
                # 综合相似度
                combined_sim = (text_sim * 0.4 + level_sim * 0.3 + subtree_sim * 0.3)
                row.append(combined_sim)
            similarities.append(row)
        
        # 使用贪心算法找到最佳匹配
        if not similarities:
            return 0.0
        
        total_similarity = 0
        matched_pairs = 0
        used_j = set()
        
        for i in range(len(similarities)):
            best_j = -1
            best_sim = 0
            for j in range(len(similarities[i])):
                if j not in used_j and similarities[i][j] > best_sim:
                    best_sim = similarities[i][j]
                    best_j = j
            
            if best_j != -1:
                total_similarity += best_sim
                matched_pairs += 1
                used_j.add(best_j)
        
        # 考虑未匹配的节点
        total_nodes = max(len(children1), len(children2))
        if total_nodes == 0:
            return 1.0
        
        return total_similarity / total_nodes
    
    def _preprocess_text(self, content: str) -> str:
        """预处理文本内容"""
        # 移除代码块
        content = re.sub(r'```[^`]*```', ' ', content, flags=re.DOTALL)
        # 移除行内代码
        content = re.sub(r'`[^`]+`', ' ', content)
        # 移除LaTeX公式
        content = re.sub(r'\$\$[^$]+\$\$', ' ', content)
        content = re.sub(r'\$[^$]+\$', ' ', content)
        # 移除Markdown标记
        content = re.sub(r'[#*_\[\]()]+', ' ', content)
        # 移除多余空白
        content = re.sub(r'\s+', ' ', content)
        return content.strip().lower()
    
    def find_optimal_clusters(self, features: np.ndarray) -> int:
        """使用轮廓系数找到最优聚类数量"""
        if len(features) < 2:
            return 1
        
        max_k = min(self.max_clusters, len(features) - 1)
        if max_k < 2:
            return 1
            
        silhouette_scores = []
        balance_scores = []
        k_range = range(2, max_k + 1)
        
        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features)
            silhouette_avg = silhouette_score(features, cluster_labels)
            
            # 计算聚类平衡性得分
            cluster_sizes = [np.sum(cluster_labels == i) for i in range(k)]
            expected_size = len(features) / k
            balance_score = 1.0 / (1.0 + np.std(cluster_sizes) / expected_size)
            
            silhouette_scores.append(silhouette_avg)
            balance_scores.append(balance_score)
            
            print(f"聚类数量 {k}: 轮廓系数 = {silhouette_avg:.3f}, 平衡性 = {balance_score:.3f}")
        
        # 综合考虑轮廓系数和平衡性
        combined_scores = [0.6 * sil + 0.4 * bal for sil, bal in zip(silhouette_scores, balance_scores)]
        optimal_k = k_range[np.argmax(combined_scores)]
        print(f"最优聚类数量: {optimal_k} (综合得分: {max(combined_scores):.3f})")
        return optimal_k
    
    def _balance_clusters(self, features: np.ndarray, initial_labels: np.ndarray) -> np.ndarray:
        """平衡聚类分布，使每个聚类的文档数量尽可能接近"""
        n_samples = len(features)
        n_clusters = len(np.unique(initial_labels))
        target_size = n_samples // n_clusters
        remainder = n_samples % n_clusters
        
        # 计算每个聚类的目标大小
        target_sizes = [target_size + (1 if i < remainder else 0) for i in range(n_clusters)]
        
        balanced_labels = initial_labels.copy()
        
        # 计算每个样本到各个聚类中心的距离
        cluster_centers = []
        for i in range(n_clusters):
            cluster_mask = initial_labels == i
            if np.sum(cluster_mask) > 0:
                center = np.mean(features[cluster_mask], axis=0)
                cluster_centers.append(center)
            else:
                cluster_centers.append(np.zeros(features.shape[1]))
        
        cluster_centers = np.array(cluster_centers)
        
        # 计算距离矩阵
        distances = np.zeros((n_samples, n_clusters))
        for i in range(n_clusters):
            distances[:, i] = np.linalg.norm(features - cluster_centers[i], axis=1)
        
        # 迭代平衡聚类
        max_iterations = 10
        for iteration in range(max_iterations):
            current_sizes = [np.sum(balanced_labels == i) for i in range(n_clusters)]
            
            # 检查是否已经平衡
            if all(abs(current_sizes[i] - target_sizes[i]) <= 1 for i in range(n_clusters)):
                break
            
            # 找到过大和过小的聚类
            oversized = [i for i in range(n_clusters) if current_sizes[i] > target_sizes[i]]
            undersized = [i for i in range(n_clusters) if current_sizes[i] < target_sizes[i]]
            
            if not oversized or not undersized:
                break
            
            # 从过大的聚类中移动样本到过小的聚类
            for over_cluster in oversized:
                if current_sizes[over_cluster] <= target_sizes[over_cluster]:
                    continue
                    
                # 找到该聚类中距离中心最远的样本
                over_mask = balanced_labels == over_cluster
                over_indices = np.where(over_mask)[0]
                over_distances = distances[over_indices, over_cluster]
                
                # 按距离排序，优先移动距离较远的样本
                sorted_indices = over_indices[np.argsort(over_distances)[::-1]]
                
                for sample_idx in sorted_indices:
                    if current_sizes[over_cluster] <= target_sizes[over_cluster]:
                        break
                    
                    # 找到最适合的目标聚类
                    sample_distances = distances[sample_idx]
                    
                    # 只考虑还需要更多样本的聚类
                    valid_targets = [i for i in undersized if current_sizes[i] < target_sizes[i]]
                    if not valid_targets:
                        break
                    
                    # 选择距离最近的目标聚类
                    target_cluster = min(valid_targets, key=lambda x: sample_distances[x])
                    
                    # 移动样本
                    balanced_labels[sample_idx] = target_cluster
                    current_sizes[over_cluster] -= 1
                    current_sizes[target_cluster] += 1
                    
                    # 更新undersized列表
                    if current_sizes[target_cluster] >= target_sizes[target_cluster]:
                        undersized.remove(target_cluster)
        
        return balanced_labels
    
    def fit_cluster(self, documents: List[str]) -> 'MarkdownClusterer':
        """训练聚类模型"""
        print(f"开始处理 {len(documents)} 个文档...")
        
        # 初始化TF-IDF向量化器
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        # 提取结构特征
        structural_features = []
        processed_texts = []
        heading_similarities = []
        
        for i, content in enumerate(documents):
            if i % 50 == 0:
                print(f"处理进度: {i}/{len(documents)}")
            
            # 结构特征
            struct_feat = self.extract_structural_features(content)
            structural_features.append(list(struct_feat.values()))
            
            # 文本特征
            processed_text = self._preprocess_text(content)
            processed_texts.append(processed_text)
        
        # 计算文档间标题相似度特征（优化版本）
        print("计算标题相似度特征...")
        
        # 对于大量文档，使用更高效的采样策略
        if len(documents) > 100:
            print("文档数量较多，使用快速采样策略...")
            # 随机采样少量文档进行相似度计算
            import random
            random.seed(42)
            
            for i, content in enumerate(documents):
                if i % 100 == 0:
                    print(f"标题相似度计算进度: {i}/{len(documents)}")
                
                # 随机采样最多5个文档进行比较
                sample_size = min(5, len(documents) - 1)
                available_indices = [j for j in range(len(documents)) if j != i]
                sample_indices = random.sample(available_indices, min(sample_size, len(available_indices)))
                
                similarities = []
                for j in sample_indices:
                    try:
                        sim_features = self.calculate_heading_similarity(content, documents[j])
                        similarities.append([
                            sim_features['heading_eds'],
                            sim_features['heading_tree_similarity'],
                            sim_features['heading_count_diff']
                        ])
                    except Exception as e:
                        # 如果计算失败，跳过这个比较
                        continue
                
                if similarities:
                    avg_similarities = np.mean(similarities, axis=0)
                    heading_similarities.append(avg_similarities.tolist())
                else:
                    heading_similarities.append([0.0, 0.0, 0.0])
        else:
            # 对于少量文档，使用原有策略
            for i, content in enumerate(documents):
                if i % 50 == 0:
                    print(f"标题相似度计算进度: {i}/{len(documents)}")
                
                similarities = []
                sample_indices = list(range(0, min(i, 5))) + list(range(max(0, i-5), i))
                
                for j in sample_indices:
                    if j != i:
                        try:
                            sim_features = self.calculate_heading_similarity(content, documents[j])
                            similarities.append([
                                sim_features['heading_eds'],
                                sim_features['heading_tree_similarity'],
                                sim_features['heading_count_diff']
                            ])
                        except Exception as e:
                            continue
                
                if similarities:
                    avg_similarities = np.mean(similarities, axis=0)
                    heading_similarities.append(avg_similarities.tolist())
                else:
                    heading_similarities.append([0.0, 0.0, 0.0])
        
        # 转换为numpy数组
        structural_features = np.array(structural_features)
        heading_similarities = np.array(heading_similarities)
        
        # TF-IDF特征提取
        print("提取TF-IDF特征...")
        tfidf_features = self.tfidf_vectorizer.fit_transform(processed_texts)
        
        # 合并特征
        # 标准化结构特征
        structural_features_scaled = self.scaler.fit_transform(structural_features)
        
        # 标准化标题相似度特征
        if heading_similarities.size > 0:
            self.heading_scaler = StandardScaler()
            heading_similarities_scaled = self.heading_scaler.fit_transform(heading_similarities)
        else:
            heading_similarities_scaled = heading_similarities
            self.heading_scaler = None
        
        # 降维TF-IDF特征
        tfidf_dense = tfidf_features.toarray()
        if tfidf_dense.shape[1] > 100:  # 如果特征太多，进行降维
            self.pca = PCA(n_components=100, random_state=42)
            tfidf_reduced = self.pca.fit_transform(tfidf_dense)
        else:
            tfidf_reduced = tfidf_dense
        
        # 合并所有特征：结构特征 + 标题相似度特征 + TF-IDF特征
        if heading_similarities_scaled.size > 0:
            combined_features = np.hstack([structural_features_scaled, heading_similarities_scaled, tfidf_reduced])
        else:
            combined_features = np.hstack([structural_features_scaled, tfidf_reduced])
        
        # 确定最优聚类数量
        if self.n_clusters is None:
            print("寻找最优聚类数量...")
            self.n_clusters = self.find_optimal_clusters(combined_features)
        
        # 训练K-means模型
        print(f"使用 {self.n_clusters} 个聚类进行训练...")
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        initial_labels = self.kmeans.fit_predict(combined_features)
        
        # 平衡聚类分布
        print("正在平衡聚类分布...")
        self.cluster_labels = self._balance_clusters(combined_features, initial_labels)
        
        # 计算聚类质量
        if len(set(self.cluster_labels)) > 1:
            silhouette_avg = silhouette_score(combined_features, self.cluster_labels)
            print(f"最终聚类轮廓系数: {silhouette_avg:.3f}")
        
        # 分析聚类分布均匀性
        cluster_sizes = [np.sum(self.cluster_labels == i) for i in range(self.n_clusters)]
        avg_size = np.mean(cluster_sizes)
        std_size = np.std(cluster_sizes)
        uniformity = 1.0 / (1.0 + std_size / avg_size) if avg_size > 0 else 0
        print(f"分布均匀性: {uniformity:.3f} (标准差: {std_size:.1f}, 平均大小: {avg_size:.1f})")
        
        # 保存训练数据和特征
        self.documents_ = documents
        self.features_ = combined_features
        
        # 分析聚类结果
        self._analyze_clusters(documents, structural_features)
        
        return self
    
    def predict_cluster(self, content: str) -> Tuple[int, Dict[str, float]]:
        """预测单个文档的聚类"""
        if self.kmeans is None:
            raise ValueError("模型尚未训练，请先调用 fit_cluster 方法")
        
        # 提取特征
        struct_feat = self.extract_structural_features(content)
        structural_features = np.array([list(struct_feat.values())])
        
        processed_text = self._preprocess_text(content)
        tfidf_features = self.tfidf_vectorizer.transform([processed_text])
        
        # 标准化和降维
        structural_features_scaled = self.scaler.transform(structural_features)
        tfidf_dense = tfidf_features.toarray()
        
        if hasattr(self.pca, 'transform'):
            tfidf_reduced = self.pca.transform(tfidf_dense)
        else:
            tfidf_reduced = tfidf_dense
        
        # 计算标题相似度特征（与训练文档的采样比较）
        heading_similarities = []
        if hasattr(self, 'documents_') and self.documents_:
            import random
            random.seed(42)
            
            # 随机采样5个训练文档进行比较
            sample_size = min(5, len(self.documents_))
            sample_indices = random.sample(range(len(self.documents_)), sample_size)
            
            similarities = []
            for j in sample_indices:
                try:
                    sim_features = self.calculate_heading_similarity(content, self.documents_[j])
                    similarities.append([
                        sim_features['heading_eds'],
                        sim_features['heading_tree_similarity'],
                        sim_features['heading_count_diff']
                    ])
                except Exception as e:
                    continue
            
            if similarities:
                avg_similarities = np.mean(similarities, axis=0)
                heading_similarities = avg_similarities.reshape(1, -1)
            else:
                heading_similarities = np.array([[0.0, 0.0, 0.0]])
        else:
            heading_similarities = np.array([[0.0, 0.0, 0.0]])
        
        # 合并特征（需要与训练时的特征结构保持一致）
        if heading_similarities.size > 0:
            # 标准化标题相似度特征（使用训练时的标准化器）
            if hasattr(self, 'heading_scaler'):
                heading_similarities_scaled = self.heading_scaler.transform(heading_similarities)
            else:
                heading_similarities_scaled = heading_similarities
            
            combined_features = np.hstack([structural_features_scaled, heading_similarities_scaled, tfidf_reduced])
        else:
            combined_features = np.hstack([structural_features_scaled, tfidf_reduced])
        
        # 计算到各个聚类中心的距离
        distances = []
        for i in range(self.n_clusters):
            cluster_mask = self.cluster_labels == i
            if np.sum(cluster_mask) > 0:
                # 使用训练时平衡后的聚类中心
                cluster_center = np.mean(self.features_[cluster_mask], axis=0)
                distance = np.linalg.norm(combined_features - cluster_center)
                distances.append(distance)
            else:
                distances.append(float('inf'))
        
        # 选择距离最近的聚类
        cluster_id = np.argmin(distances)
        
        return cluster_id, struct_feat
    
    def _analyze_clusters(self, documents: List[str], structural_features: np.ndarray):
        """分析聚类结果"""
        print("\n=== 聚类分析结果 ===")
        
        for cluster_id in range(self.n_clusters):
            cluster_mask = self.cluster_labels == cluster_id
            cluster_docs = [doc for i, doc in enumerate(documents) if cluster_mask[i]]
            cluster_features = structural_features[cluster_mask]
            
            print(f"\n聚类 {cluster_id}: {len(cluster_docs)} 个文档")
            
            if len(cluster_features) > 0:
                # 计算特征均值
                feature_means = np.mean(cluster_features, axis=0)
                feature_names = ['length', 'line_count', 'formula_density', 'table_density', 
                               'code_density', 'header_count', 'max_header_depth', 'header_variance',
                               'heading_text_length', 'heading_structure_complexity', 'heading_depth_transitions',
                               'list_density', 'link_density', 'citation_density',
                               'avg_heading_eds', 'avg_heading_tree_similarity', 'avg_heading_count_diff']
                
                print("主要特征:")
                for i, (name, value) in enumerate(zip(feature_names, feature_means)):
                    if i < len(feature_names):
                        print(f"  {name}: {value:.3f}")
    
    def cluster_file(self, file_path: Path) -> Tuple[int, Dict[str, float]]:
        """对单个文件进行聚类预测"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.predict_cluster(content)
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            return 0, {}
    
    def cluster_directory(self, input_dir: Path, output_dir: Path, auto_train: bool = True) -> Dict[int, List[Path]]:
        """批量聚类目录中的Markdown文件"""
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        if not input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        
        # 收集所有Markdown文件
        md_files = list(input_dir.rglob('*.md'))
        if not md_files:
            print(f"在 {input_dir} 中未找到Markdown文件")
            return {}
        
        print(f"找到 {len(md_files)} 个Markdown文件")
        
        # 如果需要自动训练且模型未训练
        if auto_train and self.kmeans is None:
            print("正在训练聚类模型...")
            documents = []
            for file_path in md_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    documents.append(content)
                except Exception as e:
                    print(f"读取文件 {file_path} 失败: {e}")
                    documents.append("")  # 添加空文档避免索引错误
            
            self.fit_cluster(documents)
        
        # 创建输出目录结构
        for cluster_id in range(self.n_clusters):
            (output_dir / f'cluster_{cluster_id}').mkdir(parents=True, exist_ok=True)
        
        # 聚类结果统计
        results = {i: [] for i in range(self.n_clusters)}
        clustering_details = []
        
        # 处理每个文件
        for i, file_path in enumerate(md_files, 1):
            print(f"处理文件 {i}/{len(md_files)}: {file_path.name}")
            
            cluster_id, features = self.cluster_file(file_path)
            results[cluster_id].append(file_path)
            
            # 复制文件到对应目录
            target_path = output_dir / f'cluster_{cluster_id}' / file_path.name
            try:
                shutil.copy2(file_path, target_path)
                clustering_details.append({
                    'file': file_path.name,
                    'cluster_id': cluster_id,
                    'features': features,
                    'target_path': target_path
                })
            except Exception as e:
                print(f"复制文件 {file_path} 失败: {e}")
        
        # 生成聚类报告
        self._generate_clustering_report(output_dir, results, clustering_details)
        
        return results
    
    def _generate_clustering_report(self, output_dir: Path, results: Dict[int, List[Path]], clustering_details: List[Dict]) -> None:
        """生成聚类报告"""
        from datetime import datetime
        
        report_path = output_dir / 'clustering_report.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Markdown文档聚类报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 统计信息
            total_files = sum(len(files) for files in results.values())
            f.write(f"## 统计信息\n\n")
            f.write(f"- 总文件数: {total_files}\n")
            f.write(f"- 聚类数量: {self.n_clusters}\n")
            
            for cluster_id, files in results.items():
                percentage = (len(files) / total_files * 100) if total_files > 0 else 0
                f.write(f"- 聚类 {cluster_id}: {len(files)} 个文件 ({percentage:.1f}%)\n")
            
            f.write("\n")
            
            # 聚类分布均匀性分析
            cluster_sizes = [len(files) for files in results.values()]
            if cluster_sizes:
                avg_size = sum(cluster_sizes) / len(cluster_sizes)
                variance = sum((size - avg_size) ** 2 for size in cluster_sizes) / len(cluster_sizes)
                std_dev = variance ** 0.5
                f.write(f"## 聚类分布分析\n\n")
                f.write(f"- 平均聚类大小: {avg_size:.1f}\n")
                f.write(f"- 标准差: {std_dev:.1f}\n")
                f.write(f"- 分布均匀性: {'良好' if std_dev < avg_size * 0.5 else '一般' if std_dev < avg_size else '较差'}\n\n")
            
            # 详细聚类结果
            for cluster_id, files in results.items():
                if files:
                    f.write(f"## 聚类 {cluster_id} 文档\n\n")
                    for file_path in files:
                        f.write(f"- {file_path.name}\n")
                    f.write("\n")
            
            # 特征分析
            f.write("## 聚类特征分析\n\n")
            
            # 按聚类分组分析特征
            cluster_features = {}
            for detail in clustering_details:
                cluster_id = detail['cluster_id']
                if cluster_id not in cluster_features:
                    cluster_features[cluster_id] = []
                cluster_features[cluster_id].append(detail['features'])
            
            for cluster_id, features_list in cluster_features.items():
                f.write(f"### 聚类 {cluster_id} 特征统计\n")
                if features_list:
                    # 计算平均特征值
                    feature_names = list(features_list[0].keys())
                    avg_features = {}
                    for feature_name in feature_names:
                        values = [f.get(feature_name, 0) for f in features_list if isinstance(f.get(feature_name), (int, float))]
                        if values:
                            avg_features[feature_name] = sum(values) / len(values)
                    
                    for feature, value in avg_features.items():
                        f.write(f"- {feature}: {value:.3f}\n")
                f.write("\n")
        
        print(f"聚类报告已生成: {report_path}")
    
    def save_model(self, model_path: Path) -> None:
        """保存训练好的聚类模型"""
        import pickle
        
        model_data = {
            'kmeans': self.kmeans,
            'tfidf_vectorizer': self.tfidf_vectorizer,
            'scaler': self.scaler,
            'pca': self.pca,
            'n_clusters': self.n_clusters
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"模型已保存到: {model_path}")
    
    def load_model(self, model_path: Path) -> 'MarkdownClusterer':
        """加载训练好的聚类模型"""
        import pickle
        
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.kmeans = model_data['kmeans']
        self.tfidf_vectorizer = model_data['tfidf_vectorizer']
        self.scaler = model_data['scaler']
        self.pca = model_data['pca']
        self.n_clusters = model_data['n_clusters']
        
        print(f"模型已从 {model_path} 加载")
        return self
    
    def visualize_clusters(self, output_dir: Path) -> None:
        """生成聚类可视化图表"""
        if self.cluster_labels is None:
            print("警告: 模型尚未训练，无法生成可视化")
            return
        
        try:
            import matplotlib.pyplot as plt
            from collections import Counter
            
            # 聚类分布饼图
            cluster_counts = Counter(self.cluster_labels)
            
            plt.figure(figsize=(10, 6))
            
            # 饼图
            plt.subplot(1, 2, 1)
            labels = [f'聚类 {i}' for i in cluster_counts.keys()]
            sizes = list(cluster_counts.values())
            plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            plt.title('聚类分布')
            
            # 柱状图
            plt.subplot(1, 2, 2)
            plt.bar(range(len(cluster_counts)), sizes)
            plt.xlabel('聚类ID')
            plt.ylabel('文档数量')
            plt.title('各聚类文档数量')
            plt.xticks(range(len(cluster_counts)), [f'聚类{i}' for i in cluster_counts.keys()])
            
            plt.tight_layout()
            
            # 保存图表
            chart_path = output_dir / 'cluster_visualization.png'
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"聚类可视化图表已保存: {chart_path}")
            
        except ImportError:
            print("警告: matplotlib未安装，无法生成可视化图表")


def main():
    parser = argparse.ArgumentParser(description='Markdown文档自动聚类工具')
    parser.add_argument('input_dir', help='输入目录路径')
    parser.add_argument('output_dir', help='输出目录路径')
    parser.add_argument('--clusters', type=int, help='指定聚类数量（默认自动确定）')
    parser.add_argument('--max-clusters', type=int, default=10, help='最大聚类数量')
    parser.add_argument('--save-model', help='保存训练好的模型到指定路径')
    parser.add_argument('--load-model', help='从指定路径加载预训练模型')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"错误: 输入目录 {input_dir} 不存在")
        return
    
    # 创建聚类器
    clusterer = MarkdownClusterer(
        n_clusters=args.clusters,
        max_clusters=args.max_clusters
    )
    
    # 如果指定了加载模型
    if args.load_model:
        model_path = Path(args.load_model)
        if model_path.exists():
            clusterer.load_model(model_path)
        else:
            print(f"警告: 模型文件 {model_path} 不存在，将重新训练")
    
    print("开始聚类Markdown文档...")
    results = clusterer.cluster_directory(input_dir, output_dir)
    
    # 保存模型
    if args.save_model:
        model_path = Path(args.save_model)
        clusterer.save_model(model_path)
    
    # 生成可视化图表
    clusterer.visualize_clusters(output_dir)
    
    # 打印统计信息
    print("\n=== 聚类统计 ===")
    total_files = sum(len(files) for files in results.values())
    for cluster_id, files in results.items():
        percentage = (len(files) / total_files * 100) if total_files > 0 else 0
        print(f"聚类 {cluster_id}: {len(files)}个文件 ({percentage:.1f}%)")
    
    # 分析分布均匀性
    cluster_sizes = [len(files) for files in results.values()]
    if cluster_sizes:
        avg_size = sum(cluster_sizes) / len(cluster_sizes)
        std_dev = (sum((size - avg_size) ** 2 for size in cluster_sizes) / len(cluster_sizes)) ** 0.5
        uniformity = "良好" if std_dev < avg_size * 0.5 else "一般" if std_dev < avg_size else "较差"
        print(f"\n分布均匀性: {uniformity} (标准差: {std_dev:.1f})")
    
    print("\n聚类完成!")
    print(f"\n结果已保存到: {output_dir}")
    print(f"聚类报告: {output_dir / 'clustering_report.md'}")
    print(f"可视化图表: {output_dir / 'cluster_visualization.png'}")


if __name__ == '__main__':
    main()