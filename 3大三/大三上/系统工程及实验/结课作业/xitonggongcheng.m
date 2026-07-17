clear;
clc;

function ahp_graduation_decision()
    % AHP方法进行毕业去向决策分析
    % 自动化强基计划学生毕业去向评价
    
    fprintf('=== AHP毕业去向决策分析 ===\n\n');
    
    % 定义方案名称
    alternatives = {'A:跟导师读硕', 'B:跟导师读博', 'C:其他院校读研', ...
                   'D:出国留学', 'E:考公务员', 'F:创业', 'G:直接就业'};
    
    % 定义准则名称
    criteria = {'学术发展潜力', '经济收益', '个人兴趣匹配', ...
               '工作生活平衡', '社会贡献'};
    
    % 1. 准则层判断矩阵
    criteria_matrix = [
        1,   3,   2,   4,   3;
        1/3, 1,   1/2, 2,   1;
        1/2, 2,   1,   3,   2;
        1/4, 1/2, 1/3, 1,   1/2;
        1/3, 1,   1/2, 2,   1
    ];
    
    % 2. 方案层判断矩阵（每个准则对应一个7x7矩阵）
    alternative_matrices = cell(5, 1);
    
    % 准则1: 学术发展潜力
    alternative_matrices{1} = [
        1,   1/2, 2,   1/3, 4,   5,   3;
        2,   1,   3,   1/2, 5,   6,   4;
        1/2, 1/3, 1,   1/4, 3,   4,   2;
        3,   2,   4,   1,   6,   7,   5;
        1/4, 1/5, 1/3, 1/6, 1,   2,   1/2;
        1/5, 1/6, 1/4, 1/7, 1/2, 1,   1/3;
        1/3, 1/4, 1/2, 1/5, 2,   3,   1
    ];
    
    % 准则2: 经济收益
    alternative_matrices{2} = [
        1,   1/3, 2,   1/2, 1/4, 1/5, 2;
        3,   1,   4,   2,   1/2, 1/3, 4;
        1/2, 1/4, 1,   1/3, 1/5, 1/6, 1;
        2,   1/2, 3,   1,   1/3, 1/4, 3;
        4,   2,   5,   3,   1,   1/2, 5;
        5,   3,   6,   4,   2,   1,   6;
        1/2, 1/4, 1,   1/3, 1/5, 1/6, 1
    ];
    
    % 准则3: 个人兴趣匹配
    alternative_matrices{3} = [
        1,   1/2, 3,   2,   4,   5,   3;
        2,   1,   4,   3,   5,   6,   4;
        1/3, 1/4, 1,   1/2, 2,   3,   1;
        1/2, 1/3, 2,   1,   3,   4,   2;
        1/4, 1/5, 1/2, 1/3, 1,   2,   1/2;
        1/5, 1/6, 1/3, 1/4, 1/2, 1,   1/3;
        1/3, 1/4, 1,   1/2, 2,   3,   1
    ];
    
    % 准则4: 工作生活平衡
    alternative_matrices{4} = [
        1,   1/2, 2,   1/3, 1/4, 1/5, 2;
        2,   1,   3,   1/2, 1/3, 1/4, 3;
        1/2, 1/3, 1,   1/4, 1/5, 1/6, 1;
        3,   2,   4,   1,   1/2, 1/3, 4;
        4,   3,   5,   2,   1,   1/2, 5;
        5,   4,   6,   3,   2,   1,   6;
        1/2, 1/3, 1,   1/4, 1/5, 1/6, 1
    ];
    
    % 准则5: 社会贡献
    alternative_matrices{5} = [
        1,   1/3, 2,   1/2, 3,   4,   2;
        3,   1,   4,   2,   5,   6,   4;
        1/2, 1/4, 1,   1/3, 2,   3,   1;
        2,   1/2, 3,   1,   4,   5,   3;
        1/3, 1/5, 1/2, 1/4, 1,   2,   1/2;
        1/4, 1/6, 1/3, 1/5, 1/2, 1,   1/3;
        1/2, 1/4, 1,   1/3, 2,   3,   1
    ];
    
    % 3. 层次单排序和一致性检验
    fprintf('=== 层次单排序 ===\n\n');
    
    % 准则层权重计算
    fprintf('准则层权重计算:\n');
    [criteria_weights, criteria_consistency] = calculate_weights(criteria_matrix);
    for i = 1:length(criteria)
        fprintf('%s: %.4f\n', criteria{i}, criteria_weights(i));
    end
    fprintf('一致性比率 CR = %.4f (%s)\n\n', criteria_consistency, ...
        iif(criteria_consistency < 0.1, '通过检验', '未通过检验'));
    
    % 方案层权重计算
    alternative_weights = zeros(length(alternatives), length(criteria));
    alternative_consistency = zeros(1, length(criteria));
    
    fprintf('方案层权重计算:\n');
    for i = 1:length(criteria)
        fprintf('\n准则 %d: %s\n', i, criteria{i});
        [weights, consistency] = calculate_weights(alternative_matrices{i});
        alternative_weights(:, i) = weights;
        alternative_consistency(i) = consistency;
        
        for j = 1:length(alternatives)
            fprintf('  %s: %.4f\n', alternatives{j}, weights(j));
        end
        fprintf('  一致性比率 CR = %.4f (%s)\n', consistency, ...
            iif(consistency < 0.1, '通过检验', '未通过检验'));
    end
    
    % 4. 层次总排序
    fprintf('\n=== 层次总排序 ===\n\n');
    
    total_weights = alternative_weights * criteria_weights;
    
    % 按权重排序
    [sorted_weights, sorted_indices] = sort(total_weights, 'descend');
    
    fprintf('各方案总权重排序:\n');
    for i = 1:length(alternatives)
        idx = sorted_indices(i);
        fprintf('%d. %s: %.4f\n', i, alternatives{idx}, sorted_weights(i));
    end
    
    % 5. 总排序一致性检验
    fprintf('\n=== 总排序一致性检验 ===\n\n');
    
    % 随机一致性指数RI（根据矩阵阶数）
    RI_values = [0, 0, 0.58, 0.90, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49];
    
    CI_total = 0;
    RI_total = 0;
    
    for i = 1:length(criteria)
        n = size(alternative_matrices{i}, 1);
        CI_i = (alternative_consistency(i) * RI_values(n));
        CI_total = CI_total + criteria_weights(i) * CI_i;
        RI_total = RI_total + criteria_weights(i) * RI_values(n);
    end
    
    CR_total = CI_total / RI_total;
    
    fprintf('总一致性比率 CR_total = %.4f\n', CR_total);
    fprintf('检验结果: %s\n\n', iif(CR_total < 0.1, '通过一致性检验', '未通过一致性检验'));
    
    % 6. 结果解释
    fprintf('=== 结果解释 ===\n\n');
    
    fprintf('分析结果说明:\n');
    fprintf('1. 最优选择: %s (权重: %.4f)\n', alternatives{sorted_indices(1)}, sorted_weights(1));
    fprintf('2. 次优选择: %s (权重: %.4f)\n', alternatives{sorted_indices(2)}, sorted_weights(2));
    fprintf('3. 最差选择: %s (权重: %.4f)\n\n', alternatives{sorted_indices(end)}, sorted_weights(end));
    
    % 7. 可视化结果
    visualize_results(alternatives, total_weights, criteria, criteria_weights, alternative_weights);
end

function [weights, consistency_ratio] = calculate_weights(matrix)
    % 计算判断矩阵的权重和一致性比率
    n = size(matrix, 1);
    
    % 计算权重（几何平均法）
    row_products = prod(matrix, 2);
    weights = row_products .^ (1/n);
    weights = weights / sum(weights);
    
    % 计算最大特征值
    lambda_max = max(eig(matrix));
    
    % 一致性指标
    CI = (lambda_max - n) / (n - 1);
    
    % 随机一致性指数
    RI_values = [0, 0, 0.58, 0.90, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49];
    RI = RI_values(n);
    
    % 一致性比率
    consistency_ratio = CI / RI;
end

function result = iif(condition, true_value, false_value)
    % 简化的条件判断函数
    if condition
        result = true_value;
    else
        result = false_value;
    end
end

function visualize_results(alternatives, weights, criteria, criteria_weights, alternative_weights)
    % 可视化结果
    
    figure('Position', [100, 100, 1200, 800]);
    
    % 子图1: 方案总权重柱状图
    subplot(2, 2, 1);
    bar(weights, 'FaceColor', [0.2, 0.6, 0.8]);
    title('各方案总权重排序', 'FontSize', 12, 'FontWeight', 'bold');
    xlabel('方案');
    ylabel('权重');
    set(gca, 'XTickLabel', alternatives);
    xtickangle(45);
    grid on;
    
    % 子图2: 准则权重饼图
    subplot(2, 2, 2);
    pie(criteria_weights, criteria);
    title('准则层权重分布', 'FontSize', 12, 'FontWeight', 'bold');
    
    % 子图3: 修正的雷达图 - 展示前两名方案在各准则下的表现
    subplot(2, 2, 3);
    
    [~, sorted_indices] = sort(weights, 'descend');
    top2_indices = sorted_indices(1:2);
    
    % 准备雷达图数据
    radar_data = alternative_weights(top2_indices, :)';
    
    % 创建雷达图
    categories = criteria;
    angles = linspace(0, 2*pi, length(categories)+1);
    angles = angles(1:end-1);
    
    % 绘制雷达图
    polarplot([angles, angles(1)], [radar_data(:,1); radar_data(1,1)], 'r-', 'LineWidth', 2);
    hold on;
    polarplot([angles, angles(1)], [radar_data(:,2); radar_data(1,2)], 'b-', 'LineWidth', 2);
    
    % 设置角度标签
    ax = gca;
    ax.ThetaTick = rad2deg(angles);
    ax.ThetaTickLabel = categories;
    
    title('前两名方案在各准则下表现', 'FontSize', 12, 'FontWeight', 'bold');
    legend({alternatives{top2_indices(1)}, alternatives{top2_indices(2)}}, 'Location', 'best');
    
    % 子图4: 文本说明
    subplot(2, 2, 4);
    axis off;
    
    [sorted_weights, sorted_indices] = sort(weights, 'descend');
    
    text_str = sprintf('AHP分析结论:\n\n');
    text_str = [text_str sprintf('推荐选择: %s\n权重: %.4f\n\n', ...
        alternatives{sorted_indices(1)}, sorted_weights(1))];
    text_str = [text_str sprintf('次选: %s\n权重: %.4f\n\n', ...
        alternatives{sorted_indices(2)}, sorted_weights(2))];
    text_str = [text_str sprintf('最不推荐: %s\n权重: %.4f\n\n', ...
        alternatives{sorted_indices(end)}, sorted_weights(end))];
    
    % 添加详细分析
    text_str = [text_str sprintf('详细分析:\n')];
    text_str = [text_str sprintf('- 跟导师读博在学术发展和个人兴趣匹配方面优势明显\n')];
    text_str = [text_str sprintf('- 出国留学在学术发展方面也有较好表现\n')];
    text_str = [text_str sprintf('- 创业在经济收益方面得分最高\n')];
    text_str = [text_str sprintf('- 考公务员在工作生活平衡方面表现较好\n\n')];
    
    text(0.1, 0.5, text_str, 'FontSize', 10, 'VerticalAlignment', 'middle');
    
    sgtitle('自动化强基计划学生毕业去向AHP分析结果', 'FontSize', 14, 'FontWeight', 'bold');
end

% 运行分析
ahp_graduation_decision();