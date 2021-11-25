N = int(input())

for _ in range(N):
    a, b = input().split()
    a = int(a)
    
    z = ''
    for i in b:
        z += a * i

    print(z)