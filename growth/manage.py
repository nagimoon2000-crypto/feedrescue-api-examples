"""Private operator ledger CLI; never expose this as an HTTP admin endpoint."""
import argparse
import json
from pathlib import Path
from .ledger import GrowthLedger


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,required=True,help='Private SQLite path outside the web root')
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('report',help='Recorded evidence only; missing external sales remain unknown')
    sub.add_parser('purge',help='Delete browser/validation telemetry older than 30 days')
    pilot=sub.add_parser('pilot',help='Record an actual private inquiry, not a link click')
    pilot.add_argument('--integration',required=True)
    pilot.add_argument('--qualified',action='store_true')
    pilot.add_argument('--approved',action='store_true')
    pilot.add_argument('--evidence',required=True,help='Private inquiry or approval reference')
    payment=sub.add_parser('payment',help='Record an actually collected, reconciled receipt')
    refund=sub.add_parser('refund',help='Record an actual refund against a recorded receipt')
    for command in (payment,refund):
        command.add_argument('--reconciled',required=True,action='store_true',help='I checked the actual provider receipt/refund')
        command.add_argument('--provider',required=True)
        command.add_argument('--transaction',required=True)
        command.add_argument('--amount',type=int,required=True,help='Integer minor currency units, never a quote')
        command.add_argument('--evidence',required=True)
        command.add_argument('--received',required=True,help='Actual ISO timestamp with timezone')
    payment.add_argument('--currency',choices=['USD','GBP'],required=True)
    payment.add_argument('--fee',type=int,required=True,help='Actual known fee in minor units; no assumed fee')
    refund.add_argument('--refund-id',required=True)
    cost=sub.add_parser('cost',help='Record actual compute/support/fixed expense')
    cost.add_argument('--id',required=True)
    cost.add_argument('--currency',choices=['USD','GBP'],required=True)
    cost.add_argument('--kind',choices=['compute','llm','support','fixed'],required=True)
    cost.add_argument('--amount',type=int,required=True)
    cost.add_argument('--evidence',required=True)
    cost.add_argument('--received',required=True)
    args=parser.parse_args()
    ledger=GrowthLedger(args.db)
    if args.action=='report': print(json.dumps(ledger.report(),indent=2))
    elif args.action=='purge': ledger.purge(); print('Expired telemetry purged.')
    elif args.action=='pilot':
        ledger.pilot(args.integration,args.qualified,args.approved,args.evidence)
        print('Recorded operator-reviewed pilot metadata; no access or billing entitlement changed.')
    elif args.action=='payment':
        added=ledger.payment(args.provider,args.transaction,args.currency,args.amount,args.fee,args.evidence,args.received)
        print(json.dumps({'new_receipt':added,'billing_active':False}))
    elif args.action=='refund':
        print(json.dumps({'new_refund':ledger.refund(args.provider,args.refund_id,args.transaction,args.amount,args.evidence,args.received)}))
    elif args.action=='cost':
        print(json.dumps({'new_cost':ledger.cost(args.id,args.currency,args.kind,args.amount,args.evidence,args.received)}))


if __name__=='__main__':main()
