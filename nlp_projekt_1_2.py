# -*- coding: utf-8 -*-
"""NLP_projekt_1.2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1RNv8OmRa3lnMiBCs5YqHtI4bIQwlUR75
"""

!pip install transformers datasets
!pip install --upgrade datasets transformers fsspec

from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score
import pandas as pd
import os
from google.colab import drive
drive.mount('/content/drive', force_remount=True)

def train_and_evaluate_model(model_name, dataset, output_dir):
    # Construct the full path within Google Drive
    drive_output_dir = os.path.join('/content/drive/MyDrive/', output_dir)

    # Check if model and tokenizer already exist in Google Drive
    if os.path.exists(drive_output_dir) and os.path.exists(os.path.join(drive_output_dir, 'config.json')) \
    and os.path.exists(os.path.join(drive_output_dir, 'tokenizer_config.json')):
        print(f"Loading existing model from {drive_output_dir}")
        tokenizer = AutoTokenizer.from_pretrained(drive_output_dir)
        model = AutoModelForSequenceClassification.from_pretrained(drive_output_dir)
    else:
        print(f"Training new model and saving to {drive_output_dir}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

        def preprocess_function(examples):
            return tokenizer(examples['text'], truncation=True, padding='max_length', max_length=128)

        tokenized_datasets = dataset.map(preprocess_function, batched=True)

        training_args = TrainingArguments(
            output_dir=drive_output_dir,
            report_to="none",
            eval_strategy="epoch",
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            num_train_epochs=2,
            weight_decay=0.01,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_datasets["train"].shuffle(seed=42).select(range(1000)),
            eval_dataset=tokenized_datasets["test"].shuffle(seed=42).select(range(500)),
        )

        trainer.train()

        # Create the output directory in Google Drive if it doesn't exist
        os.makedirs(drive_output_dir, exist_ok=True)

        trainer.save_model(drive_output_dir)
        tokenizer.save_pretrained(drive_output_dir)

    # Evaluation part
    def preprocess_function(examples):
        return tokenizer(examples['text'], truncation=True, padding='max_length', max_length=128)

    tokenized_datasets = dataset.map(preprocess_function, batched=True)

    trainer = Trainer(
        model=model,
        args=TrainingArguments(output_dir=drive_output_dir, report_to="none"),
        eval_dataset=tokenized_datasets["test"].shuffle(seed=42).select(range(500)),
    )


    eval_result = trainer.evaluate()
    predictions = trainer.predict(tokenized_datasets["test"].shuffle(seed=42).select(range(500)))
    predicted_labels = predictions.predictions.argmax(-1)
    true_labels = predictions.label_ids
    eval_result['eval_accuracy'] = accuracy_score(true_labels, predicted_labels)
    eval_result['eval_f1'] = f1_score(true_labels, predicted_labels, average='weighted')
    eval_result['eval_auc'] = roc_auc_score(true_labels, predictions.predictions[:, 1])

    return eval_result

# Load datasets
dataset1 = load_dataset("imdb")
dataset2 = load_dataset("rotten_tomatoes")

# Define model names and output directories (relative to MyDrive/)
model_names = ["distilbert-base-uncased", "bert-base-uncased", "roberta-base"]
output_dirs = ["my_distilbert_model", "my_bert_model", "my_roberta_model"]

# Train and evaluate models on both datasets, saving the models
results = []
for model_name, output_dir in zip(model_names, output_dirs):
    eval_result1 = train_and_evaluate_model(model_name, dataset1, output_dir + "_imdb")
    eval_result2 = train_and_evaluate_model(model_name, dataset2, output_dir + "_rotten_tomatoes")
    results.append({
        "model_name": model_name,
        "eval_result1": eval_result1,
        "eval_result2": eval_result2,
    })

# Create DataFrame for comparison
metrics = ['eval_loss', 'eval_accuracy', 'eval_f1', 'eval_auc', 'eval_runtime']
results_data = []
for result in results:
    results_data.append({
        'Model': result['model_name'],
        **{f'{metric}_imdb': result['eval_result1'].get(metric) for metric in metrics},
        **{f'{metric}_rotten_tomatoes': result['eval_result2'].get(metric) for metric in metrics},
    })

results_df = pd.DataFrame(results_data)

# Display the DataFrame with differences
display(results_df)

import matplotlib.pyplot as plt
import pandas as pd



metrics = ['eval_accuracy', 'eval_f1', 'eval_auc']
datasets = ['imdb', 'rotten_tomatoes']

for metric in metrics:
    fig, ax = plt.subplots(figsize=(10, 6))
    bar_width = 0.35
    index = range(len(results_df['Model']))

    for i, dataset in enumerate(datasets):
        ax.bar([p + bar_width * i for p in index], results_df[f'{metric}_{dataset}'], bar_width, label=dataset)

    ax.set_xlabel('Model')
    ax.set_ylabel(metric.replace('_', ' ').title())
    ax.set_title(f'{metric.replace("_", " ").title()} Comparison by Dataset')
    ax.set_xticks([p + bar_width / 2 for p in index])
    ax.set_xticklabels(results_df['Model'])
    ax.legend()

    # Set the y-axis limits
    ax.set_ylim(0.7, 0.95) # Set lower limit to 0.6 and upper limit to 1.0 (for metrics between 0 and 1)

    plt.tight_layout()
    plt.show()

"""## Text for the chat to test the model:

**✅ 1. Positive**

"I absolutely loved this movie! The story was captivating and the performances were outstanding."


**❌ 2. Negative**

"This was one of the worst films I've seen. The plot made no sense and the acting was terrible."


**⚖️ 3. Neutral, but slightly positive (challenging)**

"It wasn’t perfect, but I found it enjoyable overall and would probably watch it again."

**⚖️ 4. Neutral, but slightly negative (challenging)**

"The movie had a few interesting moments, but overall it felt too slow and uninspired."


**✅ 5. Ambiguous Sentiment**
Test borderline or contradictory opinions that may confuse the model:

"The actors did their best with a terrible script."

"I expected more, but it wasn’t entirely bad."

**✅ 6. Sarcasm and Irony**

"Oh great, another movie about saving the world. Just what we needed."

"Fantastic... if you enjoy falling asleep halfway through."

**✅ 7. Mixed Sentiment**
Include both strong positive and negative signals:

"The visuals were amazing, but the storyline was a disaster."

"Horrible pacing, yet I couldn’t stop watching because of the lead actor’s performance."

**✅ 8. Short and Vague Reviews**

"Not bad." (Positive or neutral?)

"It was fine." (Very ambiguous.)

**✅ 9. Highly Emotional vs. Flat Tone**

"This movie completely changed my life!" (Clearly positive and emotional)

"This film runs for 120 minutes and contains scenes of dialogue." (Neutral)

**✅ 10. Domain-Specific or Off-topic Language**
Test for generalization beyond typical review words:

"As a cinematographer, I appreciated the dynamic lighting choices."

"This reminded me of 90s European art films."

**✅ 11. Typos and Informal Language**

"I rly enjoyed this movy, gr8 job!!"

"It was meh. Not my typa thing."

**✅ 12. Foreign Words / Code-Switching**

"This movie was so chill, nagyon tetszett!"

"Not bad, but la musique was distracting."



"""

# Define the list of test reviews
test_reviews = [
    "I absolutely loved this movie! The story was captivating and the performances were outstanding.",
    "This was one of the worst films I've seen. The plot made no sense and the acting was terrible.",
    "It wasn’t perfect, but I found it enjoyable overall and would probably watch it again.",
    "The movie had a few interesting moments, but overall it felt too slow and uninspired.",
    "The actors did their best with a terrible script.",
    "I expected more, but it wasn’t entirely bad.",
    "Oh great, another movie about saving the world. Just what we needed.",
    "Fantastic... if you enjoy falling asleep halfway through.",
    "The visuals were amazing, but the storyline was a disaster.",
    "Horrible pacing, yet I couldn’t stop watching because of the lead actor’s performance.",
    "Not bad.",
    "It was fine.",
    "This movie completely changed my life!",
    "This film runs for 120 minutes and contains scenes of dialogue.",
    "As a cinematographer, I appreciated the dynamic lighting choices.",
    "This reminded me of 90s European art films.",
    "I rly enjoyed this movy, gr8 job!!",
    "It was meh. Not my typa thing.",
    "This movie was so chill, nagyon tetszett!",
    "Not bad, but la musique was distracting."
]

# Function to load the trained model and tokenizer
def load_sentiment_model(model_path):
    """Loads a trained sentiment analysis model and tokenizer."""
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        return tokenizer, model
    except Exception as e:
        print(f"Error loading model from {model_path}: {e}")
        return None, None

# Function to classify a list of reviews
def classify_reviews(reviews, tokenizer, model):
    """Classifies a list of reviews using the provided model and tokenizer."""
    results = []
    for review in reviews:
        inputs = tokenizer(review, truncation=True, padding='max_length', max_length=128, return_tensors="pt")
        outputs = model(**inputs)
        predictions = outputs.logits.argmax(-1)
        sentiment = "Positive" if predictions.item() == 1 else "Negative"
        results.append({"review": review, "sentiment": sentiment})
    return results

# --- Main Program Flow ---

print("Welcome to the Review Sentiment Classifier!")
print("Choose an option:")
print("1. Run Automated Tests")
print("2. Start User Chat Agent")
print("3. Exit")

while True:
    choice = input("Enter your choice (1, 2, or 3): ")

    if choice == '1':
        # --- Automated Testing ---
        print("\nRunning Automated Tests...\n")

        # Load the trained BERT model for IMDB dataset
        model_path = "/content/drive/MyDrive/my_bert_model_imdb"
        tokenizer, model = load_sentiment_model(model_path)

        if tokenizer and model:
            automated_test_results = classify_reviews(test_reviews, tokenizer, model)
            for result in automated_test_results:
                print(f"Processing review: \"{result['review']}\"")
                print(f"Sentiment: {result['sentiment']}\n")
        else:
            print("Skipping automated testing due to model loading error.")

    elif choice == '2':
        # --- User Chat Agent ---
        print("\nStarting User Chat Agent...")
        print("Type your review or 'quit' to exit.")

        # Load the trained BERT model for IMDB dataset
        model_path = "/content/drive/MyDrive/my_bert_model_imdb"
        tokenizer, model = load_sentiment_model(model_path)

        if tokenizer and model:
            while True:
                user_review = input("Enter your review: ")
                if user_review.lower() == 'quit':
                    break
                # Classify a single review by putting it in a list
                chat_result = classify_reviews([user_review], tokenizer, model)
                print(f"Sentiment: {chat_result[0]['sentiment']}")
        else:
            print("Skipping chat agent due to model loading error.")

    elif choice == '3':
        print("Exiting program.")
        break

    else:
        print("Invalid choice. Please enter 1, 2, or 3.")

print("Program finished.")