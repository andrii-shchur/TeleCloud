import os, tempfile

const_chunk_size = 104857600
const_max_size = 1520435200


def split_into_parts(input_file):
    FILESIZE = os.path.getsize(input_file)
    parts_list = []
    if FILESIZE == 0:
        raise FileNotFoundError
    with open(input_file, "rb") as f:
        c = 0
        filesize = 0
        while filesize < FILESIZE:
            part_size = 0
            first = True
            while part_size < const_max_size:
                file_name = os.path.splitext(input_file)
                part_file = '{}_part{}'.format(file_name[0], c, file_name[1])
                if first:
                    open(part_file, 'wb').close()
                    first = False
                    parts_list.append(part_file)
                    out_file = open(part_file, "ab")
                buf = bytearray(f.read(const_chunk_size))
                if not buf:
                    # we've read the entire file in, so we're done.
                    break
                part_size += len(buf)
                out_file.write(buf)
            out_file.close()

            c += 1
            filesize += part_size
    return parts_list


def rebuild_from_parts(output_file, parts_list):
    open(output_file, 'wb').close()
    with open(output_file, "ab") as f:
        for part in parts_list:

            part_file = open(part, "rb")
            while True:
                buf = part_file.read(const_chunk_size)
                if not buf:
                    break
                f.write(buf)

    return output_file


class TempFileMaker:
    def __enter__(self):
        self.fp = tempfile.NamedTemporaryFile(delete=True)
        return self.fp

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fp.close()
        try:
            os.unlink(self.fp.name)
        except FileNotFoundError:
            pass
