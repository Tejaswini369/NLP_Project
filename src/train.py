import torch
from torch import nn
from transformers import AutoTokenizer, AutoModel

class MultiTaskModel(nn.Module):
    def __init__(self, model_name, num_classes_task_a, num_classes_task_b):
        super(MultiTaskModel, self).__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        self.classifier_task_a = nn.Linear(self.encoder.config.hidden_size, num_classes_task_a)
        self.classifier_task_b = nn.Linear(self.encoder.config.hidden_size, num_classes_task_b)

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids, attention_mask=attention_mask)
        pooled_output = outputs.last_hidden_state.mean(dim=1)  # Mean pooling
        logits_task_a = self.classifier_task_a(pooled_output)
        logits_task_b = self.classifier_task_b(pooled_output)
        return logits_task_a, logits_task_b

# Define model parameters
model_name = "sentence-transformers/paraphrase-mpnet-base-v2"
num_classes_task_a = 3  # e.g., Positive, Negative, Neutral
num_classes_task_b = 2  # e.g., Positive, Negative

# Initialize the model
model = MultiTaskModel(model_name, num_classes_task_a, num_classes_task_b)
tokenizer = AutoTokenizer.from_pretrained(model_name)


# Define layer-wise learning rates
def get_optimizer_grouped_parameters(model, base_lr, lr_decay):
    # List of parameters and their associated learning rates
    grouped_parameters = [
        {
            'params': [p for n, p in model.named_parameters() if 'encoder.layer.' not in n],
            'lr': base_lr
        }
    ]

    # Assign decaying learning rates to each transformer layer
    for i, layer in enumerate(model.encoder.encoder.layer):
        lr = base_lr * (lr_decay ** i)
        grouped_parameters.append({
            'params': layer.parameters(),
            'lr': lr
        })

    return grouped_parameters

base_lr = 1e-4
lr_decay = 0.95  # Decay factor for learning rates of successive layers

# Get grouped parameters with layer-wise learning rates
optimizer_grouped_parameters = get_optimizer_grouped_parameters(model, base_lr, lr_decay)

# Define the optimizer
optimizer = torch.optim.Adam(optimizer_grouped_parameters)

# Sample sentences and labels for demonstration
sentences = [
    "This is a test sentence.",
    "Sentence transformers are great for encoding text.",
    "How do we generate embeddings for sentences?",
    "i feel pretty pathetic most of the time",
    "i have the feeling she was amused and delighted",
    "i started feeling sentimental about dolls i had as a child and so began a collection of vintage barbie dolls from the sixties",
    "i found myself feeling a little discouraged that morning",
    "i feel so worthless during those times i was struggling finding work"
]

labels_task_a = [2, 2, 2, 1, 0, 0, 1, 1]  # Dummy labels for sentence classification
labels_task_b = [1, 1, 1, 0, 1, 1, 0, 0]  # Dummy labels for sentiment analysis

# Tokenize sentences
inputs = tokenizer(sentences, padding=True, truncation=True, return_tensors="pt")
input_ids = inputs['input_ids']
attention_mask = inputs['attention_mask']

# Convert labels to tensors and ensure they match the batch size
labels_task_a = torch.tensor(labels_task_a)
labels_task_b = torch.tensor(labels_task_b)

# Define loss functions
criterion_task_a = nn.CrossEntropyLoss()
criterion_task_b = nn.CrossEntropyLoss()

# Training loop (dummy example)
for epoch in range(10):  # Example epoch count
    optimizer.zero_grad()
    logits_task_a, logits_task_b = model(input_ids, attention_mask)
    loss_task_a = criterion_task_a(logits_task_a, labels_task_a)
    loss_task_b = criterion_task_b(logits_task_b, labels_task_b)
    total_loss = loss_task_a + loss_task_b
    total_loss.backward()
    optimizer.step()
    print(f"Epoch {epoch + 1}, Loss: {total_loss.item()}")

print("Training completed.")

# Function to test the model with new sentences
def test_model(sentences):
    inputs = tokenizer(sentences, padding=True, truncation=True, return_tensors="pt")
    input_ids, attention_mask = inputs['input_ids'], inputs['attention_mask']
    model.eval()  # Set the model to evaluation mode
    with torch.no_grad():
        logits_task_a, logits_task_b = model(input_ids, attention_mask)
    predictions_task_a = torch.argmax(logits_task_a, dim=1)
    predictions_task_b = torch.argmax(logits_task_b, dim=1)
    label_mapping_task_a = {0: "Positive", 1: "Negative", 2: "Neutral"}
    label_mapping_task_b = {0: "Negative", 1: "Positive"}
    for i, sentence in enumerate(sentences):
        print(f"Sentence: {sentence}")
        print(f"Prediction Task A (Classification): {label_mapping_task_a[predictions_task_a[i].item()]}")
        print(f"Prediction Task B (Sentiment Analysis): {label_mapping_task_b[predictions_task_b[i].item()]}\n")

