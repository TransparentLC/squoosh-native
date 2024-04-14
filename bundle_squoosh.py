import base64
import hashlib
import os
import zipfile

# List of compressed file formats for use with Rsync --skip-compress=$RSYNC_SKIP_COMPRESS
# https://gist.github.com/StefanHamminga/2b1734240025f5ee916a
SKIP_COMPRESS_EXTS = {
    '.3g2',
    '.3gp',
    '.3gpp',
    '.3mf',
    '.7z',
    '.aac',
    '.ace',
    '.amr',
    '.apk',
    '.appx',
    '.appxbundle',
    '.arc',
    '.arj',
    '.asf',
    '.avi',
    '.avif',
    '.br',
    '.bz2',
    '.cab',
    '.crypt5',
    '.crypt7',
    '.crypt8',
    '.deb',
    '.dmg',
    '.drc',
    '.ear',
    '.gz',
    '.flac',
    '.flv',
    '.gpg',
    '.h264',
    '.h265',
    '.heif',
    '.iso',
    '.jar',
    '.jp2',
    '.jpg',
    '.jpeg',
    '.lz',
    '.lz4',
    '.lzma',
    '.lzo',
    '.m4a',
    '.m4p',
    '.m4v',
    '.mkv',
    '.msi',
    '.mov',
    '.mp3',
    '.mp4',
    '.mpeg',
    '.mpg',
    '.mpv',
    '.oga',
    '.ogg',
    '.ogv',
    '.opus',
    '.pack',
    '.png',
    '.qt',
    '.rar',
    '.rpm',
    '.rzip',
    '.s7z',
    '.sfx',
    '.svgz',
    '.tbz',
    '.tgz',
    '.tlz',
    '.txz',
    '.vob',
    '.webm',
    '.webp',
    '.wim',
    '.wma',
    '.wmv',
    '.xz',
    '.z',
    '.zip',
    '.zst',
}

TEXT_RESET = '\033[39m'
TEXT_RED = '\033[31m'

pakpath = 'squoosh.pak'
folder = 'squoosh/build'
salt = b'$qu0Osh-N4t1v3!!'

with zipfile.ZipFile('squoosh.pak', 'w') as archive:
    hashCtx = hashlib.blake2b(digest_size=16, salt=salt)
    for root, dirs, files in os.walk(folder):
        for p in files:
            file = os.path.join(root, p).replace('\\', '/')
            fileInArchive = file[len(folder)+1:]
            hctx = hashCtx.copy()
            hctx.update(fileInArchive.encode('utf-8'))
            fileObfuscated = base64.b85encode(hctx.digest()).decode().replace('*', '[').replace('?', ']')

            if os.path.splitext(file)[1] in SKIP_COMPRESS_EXTS or os.path.getsize(file) < 256:
                archive.compression = zipfile.ZIP_STORED
            else:
                archive.compression = zipfile.ZIP_LZMA

            with (
                open(file, 'rb') as f,
                archive.open(fileObfuscated, 'w') as g,
            ):
                while d := f.read(65536):
                    g.write(d)

            info = archive.getinfo(fileObfuscated)
            print(
                fileInArchive,
                fileObfuscated,
                f'{info.file_size} -> {info.compress_size} {TEXT_RED if info.compress_size - info.file_size > 28 else ""}({info.compress_size / info.file_size * 100:.2f}%){TEXT_RESET}',
                {
                    0: 'store',
                    8: 'deflate',
                    12: 'bzip2',
                    14: 'lzma',
                    93: 'zstandard',
                }.get(info.compress_type, f'compression#{info.compress_type}'),
                sep='\t',
            )

print(f'Packed file: {pakpath}')
print(f'Packed size: {os.path.getsize(pakpath)} bytes')
