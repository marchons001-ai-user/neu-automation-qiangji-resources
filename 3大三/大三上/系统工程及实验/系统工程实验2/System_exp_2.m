% 实验二:网络计划技术
% 采用AON网络图

clear all;
clc;

% 输入数据
activities = {'A','B','C','D','E','F','G','H','I'};
n = length(activities);

% 时间估计值
a = [2,6,6,1,8,5,3,3,5]; % 乐观时间
m = [5,9,7,4,8,14,12,6,8]; % 最可能时间
b = [8,12,8,7,8,17,21,9,11]; % 悲观时间

% 计算期望时间和方差
te = (a + 4*m + b) / 6;
variance = ((b - a)/6).^2;

% 定义每个作业的先行作业
predecessors = cell(n,1);
predecessors{1} = {}; % A
predecessors{2} = {'A'}; % B
predecessors{3} = {'A'}; % C
predecessors{4} = {'B','C'}; % D
predecessors{5} = {'A'}; % E
predecessors{6} = {'D','E'}; % F
predecessors{7} = {'C'}; % G
predecessors{8} = {'F','G'}; % H
predecessors{9} = {'H'}; % I

% 构建后继作业列表
successors = cell(n,1);
for i=1:n
    successors{i} = [];
end

for i=1:n
    pre_list = predecessors{i};
    for j=1:length(pre_list)
        pre_name = pre_list{j};
        pre_idx = find(strcmp(activities, pre_name));
        if ~isempty(pre_idx)
            successors{pre_idx} = [successors{pre_idx}, i];
        end
    end
end

% 计算入度
indegree = zeros(n,1);
for i=1:n
    pre_list = predecessors{i};
    indegree(i) = length(pre_list);
end

% 拓扑排序
order = [];
q = find(indegree == 0);
while ~isempty(q)
    node = q(1);
    q(1) = [];
    order = [order, node];
    succs = successors{node};
    for s = succs
        indegree(s) = indegree(s) - 1;
        if indegree(s) == 0
            q = [q, s];
        end
    end
end

if length(order) ~= n
    error('网络中存在环！');
end

% 前向传递计算ES和EF
ES = zeros(n,1);
EF = zeros(n,1);
for i=1:length(order)
    j = order(i);
    pre_list = predecessors{j};
    if isempty(pre_list)
        ES(j) = 0;
    else
        pre_ef = [];
        for k=1:length(pre_list)
            pre_name = pre_list{k};
            pre_idx = find(strcmp(activities, pre_name));
            pre_ef = [pre_ef, EF(pre_idx)];
        end
        ES(j) = max(pre_ef);
    end
    EF(j) = ES(j) + te(j);
end

project_duration = max(EF);

% 后向传递计算LF和LS
LF = zeros(n,1);
LS = zeros(n,1);
reverse_order = fliplr(order);
for i=1:length(reverse_order)
    j = reverse_order(i);
    succ_list = successors{j};
    if isempty(succ_list)
        LF(j) = project_duration;
    else
        succ_ls = [];
        for k=1:length(succ_list)
            s = succ_list(k);
            succ_ls = [succ_ls, LS(s)];
        end
        LF(j) = min(succ_ls);
    end
    LS(j) = LF(j) - te(j);
end

% 计算时差
TS = LS - ES; % 总时差
FF = zeros(n,1); % 自由时差
for j=1:n
    succ_list = successors{j};
    if isempty(succ_list)
        FF(j) = 0;
    else
        succ_es = [];
        for k=1:length(succ_list)
            s = succ_list(k);
            succ_es = [succ_es, ES(s)];
        end
        FF(j) = min(succ_es) - EF(j);
    end
end

% 输出结点时间参数（作业结点）
fprintf('结点时间参数:\n');
fprintf('作业\tES\tLF\t时差\n');
for i=1:n
    fprintf('%s\t%.2f\t%.2f\t%.2f\n', activities{i}, ES(i), LF(i), TS(i));
end

% 输出作业时间参数
fprintf('\n作业时间参数:\n');
fprintf('作业\tES\tEF\tLS\tLF\t单时差\t总时差\n');
for i=1:n
    fprintf('%s\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\n', activities{i}, ES(i), EF(i), LS(i), LF(i), FF(i), TS(i));
end

% 确定关键路径
critical_activities = find(TS == 0);
fprintf('\n关键作业: ');
for i=1:length(critical_activities)
    fprintf('%s ', activities{critical_activities(i)});
end
fprintf('\n');

% 查找关键路径序列
end_activities = find(cellfun(@isempty, successors));
critical_paths = {};
for i=1:length(end_activities)
    j = end_activities(i);
    if TS(j) == 0
        path = j;
        current = j;
        while true
            pre_list = predecessors{current};
            critical_pre = [];
            for k=1:length(pre_list)
                pre_name = pre_list{k};
                pre_idx = find(strcmp(activities, pre_name));
                if TS(pre_idx) == 0
                    critical_pre = [critical_pre, pre_idx];
                end
            end
            if isempty(critical_pre)
                break;
            else
                current = critical_pre(1);
                path = [current, path];
            end
        end
        critical_paths{end+1} = path;
    end
end

% 显示关键路径
fprintf('关键路径: ');
for i=1:length(critical_paths)
    path = critical_paths{i};
    for j=1:length(path)
        fprintf('%s', activities{path(j)});
        if j<length(path)
            fprintf(' -> ');
        end
    end
    fprintf('\n');
end

% 计算关键路径的期望时间和方差
if ~isempty(critical_paths)
    path = critical_paths{1};
    mean_duration = 0;
    var_duration = 0;
    for i=1:length(path)
        idx = path(i);
        mean_duration = mean_duration + te(idx);
        var_duration = var_duration + variance(idx);
    end
    fprintf('关键路径期望工期: %.2f\n', mean_duration);
    fprintf('关键路径方差: %.2f\n', var_duration);
    fprintf('关键路径标准差: %.2f\n', sqrt(var_duration));
else
    error('没有找到关键路径！');
end

% 创建图形窗口
figure('Position', [100, 100, 1200, 900]);
hold on;

% 计算节点位置（使用层次布局）
levels = zeros(n, 1);
for i = 1:length(order)
    node = order(i);
    pre_list = predecessors{node};
    if isempty(pre_list)
        levels(node) = 1;
    else
        max_level = 0;
        for j = 1:length(pre_list)
            pre_name = pre_list{j};
            pre_idx = find(strcmp(activities, pre_name));
            max_level = max(max_level, levels(pre_idx));
        end
        levels(node) = max_level + 1;
    end
end

% 为每个层次分配y坐标 - 增加纵向间距
max_level = max(levels);
node_positions = zeros(n, 2);
for level = 1:max_level
    nodes_in_level = find(levels == level);
    num_nodes = length(nodes_in_level);
    for k = 1:num_nodes
        node = nodes_in_level(k);
        node_positions(node, 1) = level * 200; % x坐标
        % 增加纵向间距，使用更大的乘数
        node_positions(node, 2) = (max_level + 1) * 150 - (k * 300 / (num_nodes + 1)); % y坐标
    end
end

% 计算节点大小（基于文本长度）
node_widths = zeros(n, 1);
node_heights = zeros(n, 1);
for i = 1:n
    % 根据作业名称长度和文本内容计算节点大小
    name_len = length(activities{i});
    node_widths(i) = 40 + name_len * 8; % 宽度与名称长度成正比
    node_heights(i) = 60; % 固定高度
end

% 绘制节点（矩形框，更清晰）
node_handles = zeros(n, 1);
for i = 1:n
    x = node_positions(i, 1);
    y = node_positions(i, 2);
    width = node_widths(i);
    height = node_heights(i);
    
    % 计算字体大小（与节点大小成比例）
    base_font_size = 10;
    name_font_size = base_font_size + round(width/20);
    param_font_size = base_font_size - 2 + round(width/30);
    
    % 关键节点用红色，非关键节点用蓝色
    if TS(i) == 0
        color = [1, 0.8, 0.8]; % 浅红色表示关键节点
        border_color = [1, 0, 0]; % 红色边框
    else
        color = [0.8, 0.8, 1]; % 浅蓝色表示非关键节点
        border_color = [0, 0, 1]; % 蓝色边框
    end
    
    % 绘制节点矩形框
    node_handles(i) = rectangle('Position', [x-width/2, y-height/2, width, height], ...
                               'Curvature', [0.2, 0.2], ...
                               'FaceColor', color, ...
                               'EdgeColor', border_color, ...
                               'LineWidth', 2);
    
    % 在节点内显示作业名称和期望时间
    text(x, y, sprintf('%s\n%.1f天', activities{i}, te(i)), ...
         'HorizontalAlignment', 'center', ...
         'FontSize', name_font_size, ...
         'FontWeight', 'bold');
    
    % 在节点上方显示ES和EF
    text(x, y+height/2+15, sprintf('ES=%.1f\nEF=%.1f', ES(i), EF(i)), ...
         'HorizontalAlignment', 'center', ...
         'FontSize', param_font_size, ...
         'Color', 'blue');
    
    % 在节点下方显示LS和LF
    text(x, y-height/2-15, sprintf('LS=%.1f\nLF=%.1f', LS(i), LF(i)), ...
         'HorizontalAlignment', 'center', ...
         'FontSize', param_font_size, ...
         'Color', 'red');
    
    % 在节点右侧显示时差信息
    text(x+width/2+20, y, sprintf('总时差=%.1f\n单时差=%.1f', TS(i), FF(i)), ...
         'HorizontalAlignment', 'left', ...
         'FontSize', param_font_size, ...
         'Color', 'green');
end

% 绘制实心箭头（边）
arrow_size = 10; % 箭头大小
for i = 1:n
    start_node = i;
    end_nodes = successors{i};
    
    for j = 1:length(end_nodes)
        end_node = end_nodes(j);
        
        % 计算箭头起点和终点
        start_pos = node_positions(start_node, :);
        end_pos = node_positions(end_node, :);
        
        % 调整起点和终点位置，使其在节点边缘
        dx = end_pos(1) - start_pos(1);
        dy = end_pos(2) - start_pos(2);
        dist = sqrt(dx^2 + dy^2);
        
        start_adj = [start_pos(1) + (node_widths(start_node)/2+5)*dx/dist, ...
                     start_pos(2) + (node_heights(start_node)/2+5)*dy/dist];
        end_adj = [end_pos(1) - (node_widths(end_node)/2+5)*dx/dist, ...
                   end_pos(2) - (node_heights(end_node)/2+5)*dy/dist];
        
        % 绘制主线
        if TS(start_node) == 0 && TS(end_node) == 0
            line_color = 'red';
            line_width = 3;
        else
            line_color = 'black';
            line_width = 2;
        end
        
        % 绘制连接线
        line([start_adj(1), end_adj(1)], [start_adj(2), end_adj(2)], ...
             'Color', line_color, 'LineWidth', line_width);
        
        % 计算箭头方向角度
        angle = atan2(dy, dx);
        
        % 绘制实心箭头头部
        arrow_x = end_adj(1) - arrow_size * cos(angle);
        arrow_y = end_adj(2) - arrow_size * sin(angle);
        
        % 创建箭头头部（三角形）
        arrow_head_x = [arrow_x, ...
                        arrow_x - arrow_size * cos(angle - pi/6), ...
                        arrow_x - arrow_size * cos(angle + pi/6), ...
                        arrow_x];
        arrow_head_y = [arrow_y, ...
                        arrow_y - arrow_size * sin(angle - pi/6), ...
                        arrow_y - arrow_size * sin(angle + pi/6), ...
                        arrow_y];
        
        % 填充箭头头部
        fill(arrow_head_x, arrow_head_y, line_color, 'EdgeColor', line_color);
        
        % 在箭头旁边显示作业时间参数
        mid_x = (start_adj(1) + end_adj(1)) / 2;
        mid_y = (start_adj(2) + end_adj(2)) / 2;
        
        % 垂直偏移量，避免文字重叠
        offset_x = 15 * sin(angle);
        offset_y = -15 * cos(angle);
        
        text(mid_x + offset_x, mid_y + offset_y, ...
             sprintf('te=%.1f\nσ²=%.2f', te(start_node), variance(start_node)), ...
             'HorizontalAlignment', 'center', ...
             'FontSize', param_font_size, ...
             'BackgroundColor', 'white', ...
             'EdgeColor', line_color);
    end
end

% 添加图例
legend_handles = [];
legend_labels = {};
if any(TS == 0)
    legend_handles(end+1) = plot(NaN, NaN, 's', 'MarkerSize', 10, 'MarkerFaceColor', [1, 0.8, 0.8], 'MarkerEdgeColor', 'red');
    legend_labels{end+1} = '关键节点';
end
if any(TS ~= 0)
    legend_handles(end+1) = plot(NaN, NaN, 's', 'MarkerSize', 10, 'MarkerFaceColor', [0.8, 0.8, 1], 'MarkerEdgeColor', 'blue');
    legend_labels{end+1} = '非关键节点';
end
legend_handles(end+1) = plot(NaN, NaN, '-r', 'LineWidth', 3);
legend_labels{end+1} = '关键路径';
legend_handles(end+1) = plot(NaN, NaN, '-k', 'LineWidth', 2);
legend_labels{end+1} = '非关键路径';

legend(legend_handles, legend_labels, 'Location', 'best');

% 添加标题
title('网络计划技术图 - AON网络图', 'FontSize', 16, 'FontWeight', 'bold');
xlabel('项目进度方向 →', 'FontSize', 12);
ylabel('并行作业层次', 'FontSize', 12);

% 添加统计信息文本框
stats_text = sprintf(['项目统计信息:\n', ...
                     '总工期: %.2f天\n', ...
                     '关键路径: %s\n', ...
                     '关键路径期望时间: %.2f天\n', ...
                     '关键路径方差: %.2f'], ...
                     project_duration, ...
                     strjoin(activities(critical_paths{1}), ' → '), ...
                     mean_duration, var_duration);

annotation('textbox', [0.02, 0.02, 0.3, 0.15], ...
           'String', stats_text, ...
           'FontSize', 10, ...
           'BackgroundColor', [0.95, 0.95, 0.95], ...
           'EdgeColor', 'black', ...
           'LineWidth', 1);

% 设置坐标轴
axis equal;
grid on;
set(gca, 'XTick', [], 'YTick', []);
xlim([min(node_positions(:,1)) - 100, max(node_positions(:,1)) + 150]);
ylim([min(node_positions(:,2)) - 100, max(node_positions(:,2)) + 100]);

% ==================== 原有概率计算部分 ====================
% 测算完工概率
fprintf('\n概率计算部分:\n');
T = 50;
Z = (T - mean_duration) / sqrt(var_duration);
p = normcdf(Z);
fprintf('工期不迟于50天的概率: %.4f\n', p);

% 计算比期望工期提前4天的概率
T_early = mean_duration - 4;
Z_early = (T_early - mean_duration) / sqrt(var_duration);
p_early = normcdf(Z_early);
fprintf('比期望工期提前4天的概率: %.4f\n', p_early);

% 添加箭头绘制函数（如果MATLAB版本较老可能没有arrow函数）
function arrow(start, stop, varargin)
    % 简化的箭头绘制函数
    p = inputParser;
    addParameter(p, 'Length', 10, @isnumeric);
    addParameter(p, 'BaseAngle', 60, @isnumeric);
    addParameter(p, 'TipAngle', 30, @isnumeric);
    addParameter(p, 'Color', 'black', @ischar);
    addParameter(p, 'LineWidth', 1, @isnumeric);
    parse(p, varargin{:});
    
    % 绘制主线
    plot([start(1), stop(1)], [start(2), stop(2)], ...
         'Color', p.Results.Color, 'LineWidth', p.Results.LineWidth);
    
    % 计算箭头方向
    dx = stop(1) - start(1);
    dy = stop(2) - start(2);
    angle = atan2(dy, dx);
    
    % 绘制箭头头部
    len = p.Results.Length;
    angle1 = angle + deg2rad(p.Results.BaseAngle);
    angle2 = angle - deg2rad(p.Results.BaseAngle);
    
    x1 = stop(1) - len * cos(angle1);
    y1 = stop(2) - len * sin(angle1);
    x2 = stop(1) - len * cos(angle2);
    y2 = stop(2) - len * sin(angle2);
    
    plot([stop(1), x1], [stop(2), y1], ...
         'Color', p.Results.Color, 'LineWidth', p.Results.LineWidth);
    plot([stop(1), x2], [stop(2), y2], ...
         'Color', p.Results.Color, 'LineWidth', p.Results.LineWidth);
end