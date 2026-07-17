import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from tqdm import tqdm

# 设置随机种子
torch.manual_seed(42)
np.random.seed(42)

# 检查GPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'使用设备: {device}')

# 读取数据
df = pd.read_csv('countrydata.csv')
print(f"数据形状: {df.shape}")

# 按照dateId=20200702分割时间序列
sequences = []
current_sequence = []

for i, row in df.iterrows():
    # 检查是否是序列开始点
    if row['dateId'] == 20200702 and current_sequence:
        # 保存当前序列并开始新序列
        sequences.append(current_sequence)
        current_sequence = []

    # 添加当前数据点到序列
    current_sequence.append(row['confirmedCount'])

# 添加最后一个序列
if current_sequence:
    sequences.append(current_sequence)

print(f"找到 {len(sequences)} 个独立的时间序列")

# 提取测试序列（第一段时序）
test_sequence = sequences[0]
train_sequences = sequences[1:]

print(f"测试序列长度: {len(test_sequence)}")
print(f"训练序列数量: {len(train_sequences)}")
print(f"训练序列长度示例: {[len(seq) for seq in train_sequences[:5]]}")

# 合并所有训练序列
train_data = np.concatenate(train_sequences).astype(float)
test_data = np.array(test_sequence).astype(float)

print(f"训练数据总长度: {len(train_data)}")
print(f"测试数据长度: {len(test_data)}")

# 数据标准化
scaler = StandardScaler()
train_data_scaled = scaler.fit_transform(train_data.reshape(-1, 1)).flatten()
test_data_scaled = scaler.transform(test_data.reshape(-1, 1)).flatten()


# 创建序列数据函数
def create_sequences(data, seq_length=30):
    sequences = []
    targets = []
    for i in range(len(data) - seq_length):
        seq = data[i:i + seq_length]
        target = data[i + seq_length]
        sequences.append(seq)
        targets.append(target)
    return np.array(sequences), np.array(targets)


# 设置序列长度
seq_length = 30
X_train, y_train = create_sequences(train_data_scaled, seq_length)
X_test, y_test = create_sequences(test_data_scaled, seq_length)

# 转换为PyTorch张量
X_train = torch.FloatTensor(X_train).unsqueeze(-1)  # (batch, seq_len, input_size)
y_train = torch.FloatTensor(y_train)
X_test = torch.FloatTensor(X_test).unsqueeze(-1)
y_test = torch.FloatTensor(y_test)

print(f"训练集形状: {X_train.shape}, {y_train.shape}")
print(f"测试集形状: {X_test.shape}, {y_test.shape}")

# 创建数据加载器
batch_size = 256
train_dataset = TensorDataset(X_train, y_train)
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)


# 定义GRU模型
class GRUPredictor(nn.Module):
    def __init__(self, input_size=1, hidden_size=128, num_layers=2, dropout=0.1):
        super(GRUPredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.gru = nn.GRU(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # GRU前向传播
        out, _ = self.gru(x)
        # 取最后一个时间步的输出
        out = out[:, -1, :]
        out = self.dropout(out)
        out = self.fc(out)
        return out.squeeze()


# 初始化模型
input_size = 1
hidden_size = 128
num_layers = 2
dropout = 0.2

model = GRUPredictor(input_size, hidden_size, num_layers, dropout).to(device)
print(model)

# 定义损失函数和优化器
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=30, factor=0.5)

# 训练参数
num_epochs = 300
patience = 30
best_loss = float('inf')
counter = 0

# 训练模型
train_losses = []
val_losses = []

model.train()
for epoch in range(num_epochs):
    epoch_loss = 0
    for batch_X, batch_y in train_loader:
        batch_X, batch_y = batch_X.to(device), batch_y.to(device)

        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        epoch_loss += loss.item()

    avg_loss = epoch_loss / len(train_loader)
    train_losses.append(avg_loss)

    # 验证损失
    model.eval()
    with torch.no_grad():
        val_X, val_y = X_test.to(device), y_test.to(device)
        val_outputs = model(val_X)
        val_loss = criterion(val_outputs, val_y)
        val_losses.append(val_loss.item())

    scheduler.step(val_loss)

    if (epoch + 1) % 10 == 0:
        print(f'Epoch [{epoch + 1}/{num_epochs}], Train Loss: {avg_loss:.6f}, Val Loss: {val_loss.item():.6f}')

    # 早停机制
    if val_loss < best_loss:
        best_loss = val_loss
        counter = 0
        torch.save(model.state_dict(), 'best_gru_model.pth')
    else:
        counter += 1
        if counter >= patience:
            print(f'早停于第 {epoch + 1} 轮')
            break

    model.train()

# 加载最佳模型
model.load_state_dict(torch.load('best_gru_model.pth'))


# 预测函数
def predict(model, data):
    model.eval()
    with torch.no_grad():
        data = data.to(device)
        predictions = model(data)
    return predictions.cpu().numpy()


# 在测试集上进行预测
test_predictions = predict(model, X_test)

# 反标准化预测结果和真实值
test_predictions_original = scaler.inverse_transform(test_predictions.reshape(-1, 1)).flatten()
y_test_original = scaler.inverse_transform(y_test.numpy().reshape(-1, 1)).flatten()


# 计算指标的函数
def calculate_metrics(true, pred):
    mae = np.mean(np.abs(true - pred))
    rmse = np.sqrt(np.mean((true - pred) ** 2))
    return mae, rmse


# 计算整体指标
total_mae, total_rmse = calculate_metrics(y_test_original, test_predictions_original)
print(f"\n整体测试集指标:")
print(f"MAE: {total_mae:.4f}")
print(f"RMSE: {total_rmse:.4f}")

# 定义测试集的分段
# 注意：由于序列长度，预测结果对应原始序列的第31-162天
segments = [
    (0, 10),  # 对应原始序列的第31-40天
    (10, 50),  # 对应原始序列的第41-80天
    (50, 90),  # 对应原始序列的第81-120天
    (90, 132)  # 对应原始序列的第121-162天
]

segment_names = ["31-40", "41-80", "81-120", "121-162"]

print(f"\n各分段指标:")
for i, (start, end) in enumerate(segments):
    if start < len(y_test_original) and end <= len(y_test_original):
        seg_true = y_test_original[start:end]
        seg_pred = test_predictions_original[start:end]
        seg_mae, seg_rmse = calculate_metrics(seg_true, seg_pred)
        print(f"{segment_names[i]}段 - MAE: {seg_mae:.4f}, RMSE: {seg_rmse:.4f}")

# 绘制训练损失
plt.figure(figsize=(12, 8))

plt.subplot(2, 1, 1)
plt.plot(train_losses, label='TRAIN LOSS')
plt.plot(val_losses, label='VAL LOSS')
plt.xlabel('EPOCHS')
plt.ylabel('LOSS')
plt.legend()
plt.title('TRAIN AND VALIDATE LOSS')

# 绘制预测结果
plt.subplot(2, 1, 2)
end_point = min(seq_length + 80, len(test_data))
plt.plot(range(seq_length, end_point), y_test_original[:end_point-seq_length], label='TRUE', alpha=0.7)
plt.plot(range(seq_length, end_point), test_predictions_original[:end_point-seq_length], label='PRED', alpha=0.7)
plt.xlabel('DAY')
plt.ylabel('confirmedCount')
plt.legend()
plt.title('TEST PREDICTIONS')

plt.tight_layout()
plt.savefig('gru_prediction_results.png', dpi=300, bbox_inches='tight')
plt.show()

# 输出一些统计信息
print(f"\n统计信息:")
print(f"训练样本数: {len(X_train)}")
print(f"测试样本数: {len(X_test)}")
print(f"批次大小: {batch_size}")
print(f"序列长度: {seq_length}")
print(f"隐藏层维度: {hidden_size}")
print(f"独立时间序列数量: {len(sequences)}")

# 保存预测结果
results_df = pd.DataFrame({
    'true_value': y_test_original,
    'predicted_value': test_predictions_original
})
results_df.to_csv('gru_predictions.csv', index=False)
print("预测结果已保存到 gru_predictions.csv")