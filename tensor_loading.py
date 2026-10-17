"""Load pinned safetensors one tensor at a time without whole-file mappings."""
import json
import math
import struct

def stream_weights(module, path):
    import torch
    dtypes = {'F32':torch.float32,'F16':torch.float16,'BF16':torch.bfloat16,
              'I64':torch.int64,'I32':torch.int32,'I16':torch.int16,'I8':torch.int8,
              'U8':torch.uint8,'BOOL':torch.bool}
    expected = module.state_dict()
    with path.open('rb') as file:
        header_length = struct.unpack('<Q',file.read(8))[0]
        if not 0 < header_length <= 16 * 1024**2:
            raise RuntimeError('Invalid model tensor header.')
        header = json.loads(file.read(header_length))
        header.pop('__metadata__',None)
        if set(header) != set(expected):
            raise RuntimeError('Model tensor names do not match this runtime.')
        data_start = 8 + header_length
        file_size = path.stat().st_size
        with torch.no_grad():
            for name,spec in header.items():
                dtype = dtypes[spec['dtype']]
                shape = spec['shape']
                begin,end = spec['data_offsets']
                length = end - begin
                item_size = torch.empty((),dtype=dtype).element_size()
                if tuple(shape) != tuple(expected[name].shape) or not 0 <= begin <= end or data_start + end > file_size or math.prod(shape) * item_size != length:
                    raise RuntimeError('Invalid model tensor dimensions or offsets.')
                data = bytearray(length)
                file.seek(data_start + begin)
                if file.readinto(data) != length:
                    raise RuntimeError('Incomplete model tensor.')
                tensor = torch.frombuffer(data,dtype=dtype).reshape(shape)
                expected[name].copy_(tensor)
