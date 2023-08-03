from flask import Flask, render_template, request, redirect, url_for, send_file
from flask import jsonify
import json
import os
import random
from gtts import gTTS
from datetime import datetime

app = Flask(__name__)


def text_to_speech(text, save_path):
    # 使用 Google Text-to-Speech 將文本轉換為語音
    tts = gTTS(text, lang="th")
    save_file = os.path.join(save_path, text + ".mp3")

    # 刪除已存在的舊檔案
    if os.path.exists(save_file):
        os.remove(save_file)

    tts.save(save_file)  # 儲存為以泰文為檔名的 MP3 檔案


def delete_audio_file(filename):
    # 刪除指定的音檔
    audio_file_path = os.path.join("C:\\Users\\user\\Desktop\\泰語", filename + ".mp3")
    if os.path.exists(audio_file_path):
        os.remove(audio_file_path)


def save_to_database(data):
    with open("quiz_database.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def load_from_database():
    if (
        os.path.exists("quiz_database.json")
        and os.path.getsize("quiz_database.json") > 0
    ):
        try:
            with open("quiz_database.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.decoder.JSONDecodeError:
            data = []
    else:
        data = []

    # 將資料從新到舊排序
    data.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return data


@app.route("/quiz")
def quiz():
    # Load data from the database
    # 將 quizData 轉換為 JSON 格式並傳遞給模板
    ALL_data = load_from_database()
    ALL_quizData = json.dumps(ALL_data)

    data = load_from_database()

    # Get the total number of questions from the loaded data
    total_questions = len(data)

    # Get the number of questions requested by the user from the query parameter
    num_of_questions = int(request.args.get("numOfQuestions", total_questions))

    # Ensure the number of questions is within the valid range
    num_of_questions = max(1, min(num_of_questions, total_questions))

    # Randomly select `num_of_questions` questions from the data
    selected_questions = random.sample(data, num_of_questions)

    # Convert selected questions to JSON format and pass it to the template
    quizData = json.dumps(selected_questions)
    return render_template("quiz.html", quizData=quizData, ALL_quizData=ALL_quizData)


@app.route("/play_audio/<path:filename>")
def play_audio(filename):
    audio_file = f"C:/Users/user/Desktop/泰語/{filename}.mp3"
    return send_file(audio_file)


@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    data = load_from_database()
    quizData = json.loads(request.form.get("quizData"))
    formData = request.form

    score = 0
    incorrect_questions = []

    for index, quiz in enumerate(quizData):
        selected_option = formData.get(f"question-{index}")
        if selected_option == quiz["answer"]:
            score += 1
        else:
            incorrect_questions.append(
                {"question": quiz["question"], "answer": quiz["answer"]}
            )

    total_questions = len(quizData)
    percentage = (score / total_questions) * 100

    # 回傳得分和回答錯誤的題目
    return jsonify(
        {
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "incorrect_questions": incorrect_questions,
        }
    )


@app.route("/delete/<int:index>", methods=["DELETE"])
def delete_quiz(index):
    data = load_from_database()

    if 0 <= index < len(data):
        # 刪除對應的音檔
        delete_audio_file(data[index]["question"])

        del data[index]
        save_to_database(data)
        return jsonify({"success": True})  # 使用 jsonify 返回 JSON 格式的回應，表示刪除成功
    else:
        return jsonify({"success": False}), 404  # 使用 jsonify 返回 JSON 格式的回應，表示刪除失敗


@app.route("/delete_all", methods=["DELETE"])
def delete_all_quizzes():
    data = load_from_database()

    # 刪除所有資料的同時，也刪除所有音檔
    for quiz in data:
        delete_audio_file(quiz["question"])

    data = []
    save_to_database(data)
    return {"success": True}  # 返回 JSON 格式的回應，表示刪除成功


@app.route("/update/<int:index>", methods=["PUT"])
def update_quiz(index):
    data = load_from_database()

    if 0 <= index < len(data):
        updated_quiz = request.get_json()

        # 檢查題目是否有修改
        old_question = data[index]["question"]
        new_question = updated_quiz["question"]
        if old_question != new_question:
            # 檢查是否已有相同題目
            if any(quiz["question"] == new_question for quiz in data):
                return jsonify({"success": False, "message": "相同題目已存在，請重新輸入。"})

            # 刪除舊的 mp3 檔案並重新生成新的 mp3 檔案
            old_mp3_file = os.path.join(
                "C:\\Users\\user\\Desktop\\泰語", old_question + ".mp3"
            )

            if os.path.exists(old_mp3_file):
                os.remove(old_mp3_file)

            text_to_speech(new_question, "C:\\Users\\user\\Desktop\\泰語")

        # Update the timestamp with the current time
        updated_quiz["timestamp"] = datetime.now().timestamp()

        data[index] = updated_quiz
        save_to_database(data)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 404


@app.route("/")
def index():
    data = load_from_database()
    return render_template("index.html", quizzes=data, index_start=0)


def convert_answer_to_text(quiz_options, answer_index):
    # 將選項數字轉換為對應的選項文本
    return quiz_options[answer_index]


@app.route("/add", methods=["GET", "POST"])
def add_quiz():
    if request.method == "POST":
        question = request.form.get("question")
        answer_index = request.form.get("answer")  # 因為index是從0開始的，所以減1

        data = load_from_database()

        # 檢查是否已有相同題目
        if any(quiz["question"] == question for quiz in data):
            return "相同題目已存在，請重新輸入。"

        quiz = {
            "question": question,
            "answer": answer_index,
            "timestamp": datetime.now().timestamp(),  # 加入時間戳記欄位
        }

        # 呼叫 text_to_speech 函式，將題目轉換為語音並存成 mp3 檔案
        save_path = "C:/Users/user/Desktop/泰語/"
        text_to_speech(question, save_path)

        data.append(quiz)
        save_to_database(data)

        return redirect(url_for("index"))

    return render_template("add_quiz.html")


@app.route("/check_duplicate/<string:question>")
def check_duplicate_question(question):
    data = load_from_database()

    # 檢查資料庫中是否已經存在相同的題目
    exists = any(quiz["question"] == question for quiz in data)
    return jsonify({"exists": exists})


if __name__ == "__main__":
    app.run(debug=True)
