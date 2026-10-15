#!/usr/bin/env python3
"""Offline consumer tests for the installed indi-pentax executables."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

FIXTURE_SHA256 = {
    'color.jpg': '12ed4a895e799daf48e3b1dcbd1bacbd4fb01a6a55943d4b224e129d64856ecd',
    'gray.jpg': 'b427859c7992cfee5d3a5e18a1dcb8f04cdc2f28ac773d3df329cb1f8ddb79b8',
    'bayer.dng': 'd84e65e61d78946ed600571570cdc813dd1231e96a7631cc558bf46bbe777540',
}


def restore_fixtures(encoded_dir, destination):
    """Restore byte-identical inputs from text-only PR transport."""
    destination.mkdir()
    for name, expected in FIXTURE_SHA256.items():
        encoded = (encoded_dir / (name + '.b64')).read_bytes()
        data = base64.b64decode(b''.join(encoded.split()), validate=True)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Fixture checksum mismatch: ' + name)
        (destination / name).write_bytes(data)
    (destination / 'invalid.raw').write_bytes((encoded_dir / 'invalid.raw').read_bytes())

def fits_read(path):
    data=path.read_bytes();header={};position=0
    while position+80<=len(data):
        card=data[position:position+80].decode('ascii');position+=80
        key=card[:8].strip()
        if key=='END':break
        if card[8:10]=='= ':
            value=card[10:].split('/')[0].strip()
            try:value=int(value)
            except ValueError:value=value.strip("' ")
            header[key]=value
    offset=(position+2879)//2880*2880
    count=header['NAXIS1']*header['NAXIS2']*header.get('NAXIS3',1)
    bitpix=header['BITPIX']
    if bitpix==8:pixels=list(data[offset:offset+count])
    elif bitpix==16:
        raw=struct.unpack('>'+str(count)+'h',data[offset:offset+count*2])
        pixels=[v*header.get('BSCALE',1)+header.get('BZERO',0) for v in raw]
    else:raise AssertionError('Unexpected FITS BITPIX '+str(bitpix))
    return header,pixels

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bin-dir',required=True)
    parser.add_argument('--report',default='consumer-results.json')
    args=parser.parse_args()
    encoded_fixtures=Path(__file__).resolve().parent/'fixtures'
    bindir=Path(args.bin_dir).resolve();results=[];commands=[]
    def command(argv,input_text=None):
        print('[STEP] '+' '.join(map(str,argv)),flush=True)
        p=subprocess.run(list(map(str,argv)),input=input_text,capture_output=True,text=True,timeout=30)
        print('[EXIT]',p.returncode,'\n[STDOUT]\n'+(p.stdout or '<empty>')+'\n[STDERR]\n'+(p.stderr or '<empty>'),flush=True)
        commands.append({'argv':list(map(str,argv)),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        return p
    def case(name,action):
        try:action();result={'name':name,'status':'pass'};print('[PASS]',name,flush=True)
        except Exception as e:result={'name':name,'status':'fail','error':str(e)};print('[FAIL]',name,str(e),flush=True)
        results.append(result)
    def require(condition,message):
        if not condition:raise AssertionError(message)
    image=bindir/'indi_pentax_image';driver=bindir/'indi_pentax'
    with tempfile.TemporaryDirectory(prefix='indi-pentax-consumer-') as temp:
        temp=Path(temp)
        fixtures=temp/'fixtures'
        restore_fixtures(encoded_fixtures, fixtures)
        def convert_jpeg(filename,dimensions,expected):
            output=temp/(filename+'.fits');p=command([image,'jpeg',fixtures/filename,output])
            require(p.returncode==0,'conversion failed')
            h,pix=fits_read(output)
            require((h['NAXIS1'],h['NAXIS2'])==dimensions,'image dimensions changed')
            planes=h.get('NAXIS3',1)
            require(planes==len(expected),'channel count changed')
            size=dimensions[0]*dimensions[1]
            require(len(pix)==size*planes,'pixel payload length mismatch')
            for i,value in enumerate(expected):
                require(all(abs(v-value)<=2 for v in pix[i*size:(i+1)*size]),'channel pixels differ from known fixture')
        case('color-jpeg-planar-fits',lambda:convert_jpeg('color.jpg',(16,12),(200,70,30)))
        case('grayscale-jpeg-fits',lambda:convert_jpeg('gray.jpg',(13,9),(123,)))
        def raw():
            output=temp/'bayer.fits';p=command([image,'raw',fixtures/'bayer.dng',output])
            require(p.returncode==0,'RAW conversion failed')
            h,pix=fits_read(output)
            require((h['NAXIS1'],h['NAXIS2'],h['BITPIX'])==(32,24,16),'RAW layout changed')
            require(h.get('BAYERPAT')=='RGGB','Bayer pattern mismatch')
            require(pix==list(range(1000,1000+32*24)),'RAW sample values changed')
        case('dng-bayer-fits',raw)
        def bad_input(mode,path):
            output=temp/'failure.fits';p=command([image,mode,path,output])
            require(p.returncode==3 and 'Image decode failed:' in p.stderr,'decode error contract mismatch')
            require(not output.exists(),'invalid input created output')
        case('missing-jpeg',lambda:bad_input('jpeg',temp/'missing.jpg'))
        case('invalid-raw',lambda:bad_input('raw',fixtures/'invalid.raw'))
        case('invalid-jpeg',lambda:bad_input('jpeg',fixtures/'invalid.raw'))
        def corrupt_scan():
            data=(fixtures/'color.jpg').read_bytes()
            marker=data.index(b'\xff\xda')
            start=marker+2+int.from_bytes(data[marker+2:marker+4],'big')
            path=temp/'corrupt-scan.jpg'
            path.write_bytes(data[:start]+b'\xff\xd8'+data[start:])
            bad_input('jpeg',path)
        case('jpeg-error-after-header',corrupt_scan)
        def existing():
            path=temp/'existing.fits';path.write_bytes(b'keep-existing-output')
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            p=command([image,'jpeg',fixtures/'color.jpg',path])
            require(p.returncode==4 and 'FITSIO status' in p.stderr,'existing output error contract mismatch')
            require(hashlib.sha256(path.read_bytes()).hexdigest()==before,'existing output changed')
        case('existing-output-preserved',existing)
        def invalid_args():
            p=command([image,'unsupported'])
            require(p.returncode==2 and 'Usage:' in p.stderr,'usage/error contract mismatch')
        case('invalid-arguments',invalid_args)
        def driver_no_camera():
            p=command([driver],'<getProperties version="1.7"/>\n')
            # INDI indidrivermain.c clientMsgCB exits 1 when this pipe closes.
            require(p.returncode==1 and 'indi_pentax: EOF' in p.stderr,'driver EOF contract mismatch')
            require('No supported Pentax cameras were found' in p.stderr,'expected no-camera diagnostic missing')
            require('Looking for Pentax camera in MSC mode' in p.stderr,'MSC backend not executed')
        case('driver-empty-enumeration',driver_no_camera)
    report={'cases':results,'commands':commands,'discovered':len(results),'executed':len(results),'passed':sum(r['status']=='pass' for r in results),'failed':sum(r['status']=='fail' for r in results),'skipped':0,'hardware_capture':'not executed: no camera available'}
    Path(args.report).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('RESULT',json.dumps({k:v for k,v in report.items() if k not in ('commands','cases')}),flush=True)
    return 1 if report['failed'] else 0

if __name__=='__main__':raise SystemExit(main())
