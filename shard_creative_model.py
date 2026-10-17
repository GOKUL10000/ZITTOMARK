"""Repack pinned creative weights into smaller files without changing tensors."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
from runtime_paths import APP, RUNTIME

def sha256(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file,'sha256').hexdigest()

def repack(original, destination, expected_sha, max_bytes=160*1024**2):
    if sha256(original) != expected_sha:
        raise ValueError('Creative checkpoint checksum mismatch. Run the downloader again.')
    destination.mkdir(parents=True,exist_ok=True)
    with original.open('rb') as file:
        header_size = struct.unpack('<Q',file.read(8))[0]
        if not 0 < header_size <= 16*1024**2:
            raise ValueError('Invalid model tensor header.')
        header = json.loads(file.read(header_size))
    data_start = 8 + header_size
    items = [(name,spec) for name,spec in header.items() if name != '__metadata__']
    groups, group, size = [], [], 0
    for name,spec in items:
        begin,end = spec['data_offsets']
        if not 0 <= begin <= end or data_start+end > original.stat().st_size:
            raise ValueError('Invalid model tensor offsets.')
        length = end-begin
        if group and size+length > max_bytes:
            groups.append(group); group=[];size=0
        group.append((name,spec));size+=length
    if group: groups.append(group)
    weights,checksums = {},{}
    for number,group in enumerate(groups,1):
        name = f'model-{number:05d}-of-{len(groups):05d}.safetensors'
        new_header,offset = {'__metadata__':{'format':'pt'}},0
        for key,spec in group:
            length = spec['data_offsets'][1]-spec['data_offsets'][0]
            new_header[key] = dict(spec,data_offsets=[offset,offset+length])
            weights[key] = name;offset+=length
        encoded = json.dumps(new_header,separators=(',',':')).encode()
        encoded += b' ' * (-len(encoded)%8)
        partial = destination/(name+'.partial')
        written = hashlib.sha256()
        with original.open('rb') as src,partial.open('wb') as out:
            out.write(struct.pack('<Q',len(encoded)));out.write(encoded)
            for _,spec in group:
                begin,end = spec['data_offsets'];src.seek(data_start+begin);remaining=end-begin
                while remaining:
                    block=src.read(min(8*1024**2,remaining))
                    if not block: raise ValueError('Incomplete model tensor.')
                    out.write(block);written.update(block);remaining-=len(block)
        with partial.open('rb') as saved:
            saved.seek(8+len(encoded))
            if hashlib.file_digest(saved,'sha256').digest()!=written.digest():
                raise ValueError('Creative shard verification failed.')
        os.replace(partial,destination/name)
        checksums[name]=sha256(destination/name)
        print(f'Verified creative shard {number}/{len(groups)}',flush=True)
    index={'metadata':{'total_size':original.stat().st_size-data_start},'weight_map':weights}
    (destination/'model.safetensors.index.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
    return {'original_sha256':expected_sha,'tensor_count':len(items),'tensor_bytes_unchanged':True,'shards':checksums}

def main():
    source = RUNTIME/'models'/'qwen-design'
    destination = RUNTIME/'models'/'qwen-design-sharded'
    manifest=json.loads((APP/'creative-model-manifest.json').read_text(encoding='utf-8'))
    original=next(item for item in manifest if item['file']=='model.safetensors')
    report=repack(source/'model.safetensors',destination,original['sha256'])
    for item in manifest:
        if item['file']=='model.safetensors':continue
        file=source/item['file'];target=destination/item['file']
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            try:os.link(file,target)
            except OSError:shutil.copy2(file,target)
    (destination/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Creative weights repacked and verified. Original downloaded weights retained.',flush=True)

if __name__=='__main__':main()
