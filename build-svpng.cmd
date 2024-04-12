gcc -Wall -Ofast -march=native -mtune=native -shared -o libsvpng.dll svpng.c
strip libsvpng.dll
