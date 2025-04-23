document.addEventListener('DOMContentLoaded', function () {
    const submitButton = document.getElementById('submit');
    const questionInput = document.getElementById('question');
    const answerBox = document.getElementById('answer');
    const contextsList = document.getElementById('contexts');

    submitButton.addEventListener('click', function () {
        const question = questionInput.value.trim();

        if (!question) {
            alert('请输入您的问题！');
            return;
        }


        answerBox.textContent = "正在查询，请稍候...";
        contextsList.innerHTML = "";


        fetch('http://127.0.0.1:5000/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: question })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    answerBox.textContent = data.answer;


                    contextsList.innerHTML = "";
                    data.contexts.forEach((ctx, index) => {
                        const listItem = document.createElement('li');
                        listItem.textContent = `[参考资料${index + 1}] ${ctx.text}`;
                        contextsList.appendChild(listItem);
                    });
                } else {
                    answerBox.textContent = "查询失败：" + data.answer;
                }
            })
            .catch(error => {
                console.error('发生错误:', error);
                answerBox.textContent = "服务器发生错误，请稍后再试。";
            });
    });
});