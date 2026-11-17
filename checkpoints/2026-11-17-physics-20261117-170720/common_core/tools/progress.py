"""Explicit progress ingestion and traceable weekly-source summary."""
import argparse
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.progress import append_event,event_from_receipt,summary,checked_path,ROOT

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ledger',type=Path,required=True)
    parser.add_argument('--receipt',type=Path);parser.add_argument('--status',choices=['COMPLETE','FAILED','INCOMPLETE'])
    parser.add_argument('--commit');parser.add_argument('--gate',type=Path,action='append',default=[])
    parser.add_argument('--summary',type=Path);args=parser.parse_args()
    if args.receipt:
        if not args.status:parser.error('--status required with --receipt')
        print('APPENDED' if append_event(args.ledger,event_from_receipt(args.receipt,args.status,args.commit,args.gate)) else 'ALREADY_RECORDED')
    if args.summary:
        output=checked_path(args.summary,ROOT/'_common_core_planning')
        with output.open('x',encoding='utf-8') as stream:stream.write(summary(args.ledger))
