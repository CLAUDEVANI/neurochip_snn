import math
import os

def generate_aer_stimuli(filename="build/aer_stimuli.hex", num_samples=200, threshold=0.35):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Sinal elétrico: senoide 60 Hz com surto/anomalia entre t=80 e t=120
    signal = []
    for n in range(num_samples):
        val = math.sin(2 * math.pi * n / 40.0)
        if 80 <= n <= 120:
            val += 0.9 * math.sin(2 * math.pi * n / 6.0)  # Transiente de alta frequência
        signal.append(val)

    # Codificação Delta (como sensores neuromórficos reais)
    # 0 = sem pulso | 2 (10b) = valid=1, addr=0 (subida) | 3 (11b) = valid=1, addr=1 (descida)
    ref = signal[0]
    events = []
    up_count = 0
    down_count = 0

    for val in signal:
        diff = val - ref
        if diff >= threshold:
            events.append(2)  # Subida -> Sinapse 0
            ref = val
            up_count += 1
        elif diff <= -threshold:
            events.append(3)  # Descida -> Sinapse 1
            ref = val
            down_count += 1
        else:
            events.append(0)  # Silêncio (economia de energia)

    with open(filename, "w") as f:
        for ev in events:
            f.write(f"{ev:x}\n")

    print(f"Estímulos gerados em {filename}: {num_samples} ciclos | UP(addr=0): {up_count} | DOWN(addr=1): {down_count}")

if __name__ == "__main__":
    generate_aer_stimuli()