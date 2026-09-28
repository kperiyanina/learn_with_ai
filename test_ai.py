from ai import ask_groq


response = ask_groq(
    "Ответь одним предложением: "
    "почему полезно составлять план обучения?"
)


print(response)