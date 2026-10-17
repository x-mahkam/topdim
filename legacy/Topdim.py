import json

elonlar = []

try:
    with open("elonlar.json", "r", encoding="utf-8") as fayl:
        eski_elonlar = json.load(fayl)

    for elon in eski_elonlar:
        if len(elon) == 4:
            elonlar.append(["YO‘QOLGAN"] + elon)
        else:
            elonlar.append(elon)

except FileNotFoundError:
    elonlar = []


while True:
    print()
    print("============================")
    print("          TOPDIM")
    print("============================")
    print("1. Buyumim yo‘qoldi")
    print("2. Buyum topdim")
    print("3. Buyum qidirish")
    print("4. Barcha e'lonlarni ko‘rish")
    print("5. E'lonni o‘chirish")
    print("6. Chiqish")
    print("============================")
    print()

    tanlov = input("Tanlang: ")

    if tanlov == "1":
        print()
        print("=== YO‘QOLGAN BUYUM ===")

        nomi = input("Buyum nomi: ")
        joyi = input("Qayerda yo‘qoldi: ")
        sana = input("Qachon yo‘qoldi: ")
        tavsif = input("Qo‘shimcha ma'lumot: ")

        elonlar.append(["YO‘QOLGAN", nomi, joyi, sana, tavsif])

        with open("elonlar.json", "w", encoding="utf-8") as fayl:
            json.dump(elonlar, fayl, ensure_ascii=False, indent=4)

        print()
        print("=== E'LON QABUL QILINDI ===")
        print("Turi: YO‘QOLGAN")
        print("Buyum:", nomi)
        print("Joy:", joyi)
        print("Sana:", sana)
        print("Tavsif:", tavsif)
        print()

    elif tanlov == "2":
        print()
        print("=== TOPILGAN BUYUM ===")

        nomi = input("Buyum nomi: ")
        joyi = input("Qayerdan topildi: ")
        sana = input("Qachon topildi: ")
        tavsif = input("Qo‘shimcha ma'lumot: ")

        elonlar.append(["TOPILGAN", nomi, joyi, sana, tavsif])

        with open("elonlar.json", "w", encoding="utf-8") as fayl:
            json.dump(elonlar, fayl, ensure_ascii=False, indent=4)

        print()
        print("=== E'LON QABUL QILINDI ===")
        print("Turi: TOPILGAN")
        print("Buyum:", nomi)
        print("Joy:", joyi)
        print("Sana:", sana)
        print("Tavsif:", tavsif)
        print()

    elif tanlov == "3":
        print()
        print("=== BUYUM QIDIRISH ===")

        qidiruv = input("Buyum nomi, joyi yoki tavsifi: ").lower()
        topildi = False

        for elon in elonlar:
            turi = elon[0]
            nomi = elon[1]
            joyi = elon[2]
            sana = elon[3]
            tavsif = elon[4]

            if (qidiruv in nomi.lower()
                    or qidiruv in joyi.lower()
                    or qidiruv in tavsif.lower()):

                print()
                print("Turi:", turi)
                print("Buyum:", nomi)
                print("Joy:", joyi)
                print("Sana:", sana)
                print("Tavsif:", tavsif)
                print()

                topildi = True

        if not topildi:
            print()
            print("Bunday buyum topilmadi.")
            print()

    elif tanlov == "4":
        print()
        print("=== BARCHA E'LONLAR ===")

        if len(elonlar) == 0:
            print("Hozircha e'lonlar mavjud emas.")

        else:
            for i in range(len(elonlar)):
                print()
                print(i + 1, ".", elonlar[i][0])
                print("Buyum:", elonlar[i][1])
                print("Joy:", elonlar[i][2])
                print("Sana:", elonlar[i][3])
                print("Tavsif:", elonlar[i][4])

        print()

    elif tanlov == "5":
        print()
        print("=== E'LONNI O‘CHIRISH ===")

        if len(elonlar) == 0:
            print("Hozircha e'lonlar mavjud emas.")

        else:
            for i in range(len(elonlar)):
                print()
                print(i + 1, ".", elonlar[i][0])
                print("Buyum:", elonlar[i][1])
                print("Joy:", elonlar[i][2])
                print("Sana:", elonlar[i][3])
                print("Tavsif:", elonlar[i][4])

            print()

            raqam_matn = input("O‘chiriladigan e'lon raqami: ")

            if raqam_matn.isdigit():
                raqam = int(raqam_matn)

                if 1 <= raqam <= len(elonlar):
                    elonlar.pop(raqam - 1)

                    with open("elonlar.json", "w", encoding="utf-8") as fayl:
                        json.dump(elonlar, fayl, ensure_ascii=False, indent=4)

                    print()
                    print("E'lon muvaffaqiyatli o‘chirildi.")

                else:
                    print("Bunday raqam mavjud emas.")

            else:
                print("Iltimos, raqam kiriting.")

        print()

    elif tanlov == "6":
        print()
        print("TOPDIM dasturidan chiqildi.")
        break

    else:
        print()
        print("Bunday tanlov mavjud emas.")
        print()