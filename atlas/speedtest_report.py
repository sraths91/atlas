#!/usr/bin/env python3
"""
Speed Test Report Generator - CLI tool for analyzing fleet speed test data
"""
import argparse
import sys
import logging
from fleet_speedtest_aggregator import SpeedTestAggregator


def main():
    parser = argparse.ArgumentParser(description='Generate speed test reports for fleet machines')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                        help='Report format (default: text)')
    parser.add_argument('--hours', type=int, default=24,
                        help='Number of hours to analyze (default: 24)')
    parser.add_argument('--machine', type=str,
                        help='Specific machine ID to analyze')
    parser.add_argument('--comparison', action='store_true',
                        help='Generate comparison report across all machines')
    parser.add_argument('--anomalies', action='store_true',
                        help='Detect anomalies for specified machine')
    parser.add_argument('--recent20', action='store_true',
                        help='Show average of recent 20 tests per machine')
    parser.add_argument('--subnet', type=str,
                        help='Analyze by subnet (e.g., 192.168.1.0/24)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create aggregator
    aggregator = SpeedTestAggregator()
    
    # Generate requested report
    if args.subnet:
        # Subnet analysis
        print(f"\n{'='*60}")
        if args.subnet:
            print(f"SUBNET ANALYSIS - {args.subnet}")
        else:
            print(f"SUBNET ANALYSIS - All Subnets")
        print(f"{'='*60}\n")
        
        analysis = aggregator.get_subnet_analysis(args.subnet)
        
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            sys.exit(1)
        
        print(f"Total Subnets: {analysis['total_subnets']}")
        print(f"Total Tests: {analysis['total_tests']}")
        
        print(f"\n{'Subnet Performance':-^60}")
        
        for subnet, data in sorted(analysis['subnets'].items()):
            print(f"\n{subnet}:")
            print(f"  Machines: {data['machine_count']} ({', '.join(data['machines'])})")
            print(f"  IPs: {data['ip_count']}")
            print(f"  Tests: {data['test_count']}")
            print(f"  Download: {data['avg_download_mbps']:.2f} Mbps (range: {data['min_download_mbps']:.2f} - {data['max_download_mbps']:.2f})")
            print(f"  Upload:   {data['avg_upload_mbps']:.2f} Mbps")
            print(f"  Ping:     {data['avg_ping_ms']:.2f} ms")
        
        if args.format == 'json':
            import json
            print(f"\n{'JSON Data':-^60}")
            print(json.dumps(analysis, indent=2))
    
    elif args.recent20:
        # Recent 20 average
        print(f"\n{'='*60}")
        if args.machine:
            print(f"RECENT 20 TESTS AVERAGE - {args.machine}")
        else:
            print(f"RECENT 20 TESTS AVERAGE - All Machines")
        print(f"{'='*60}\n")
        
        results = aggregator.get_recent_20_average(args.machine)
        
        if 'error' in results:
            print(f"Error: {results['error']}")
            sys.exit(1)
        
        if args.machine:
            # Single machine
            print(f"Machine: {results['machine_id']}")
            print(f"Tests Used: {results['test_count']}/20")
            print(f"\nAverages:")
            print(f"  Download: {results['avg_download_mbps']:.2f} Mbps")
            print(f"  Upload:   {results['avg_upload_mbps']:.2f} Mbps")
            print(f"  Ping:     {results['avg_ping_ms']:.2f} ms")
            print(f"  Jitter:   {results['avg_jitter_ms']:.2f} ms")
            print(f"  Packet Loss: {results['avg_packet_loss']:.2f}%")
        else:
            # All machines
            print(f"{'Machine':<20} {'Tests':>6} {'Download':>10} {'Upload':>10} {'Ping':>8}")
            print(f"{'-'*60}")
            
            for machine_id, data in sorted(results.items()):
                print(f"{machine_id:<20} "
                      f"{data['test_count']:>6} "
                      f"{data['avg_download_mbps']:>10.2f} "
                      f"{data['avg_upload_mbps']:>10.2f} "
                      f"{data['avg_ping_ms']:>8.2f}")
        
        if args.format == 'json':
            import json
            print(f"\n{'JSON Data':-^60}")
            print(json.dumps(results, indent=2))
    
    elif args.machine and args.anomalies:
        # Anomaly detection for specific machine
        print(f"\n{'='*60}")
        print(f"ANOMALY DETECTION - {args.machine}")
        print(f"{'='*60}\n")
        
        anomalies = aggregator.detect_anomalies(args.machine)
        
        if not anomalies:
            print("No anomalies detected - all speed tests within normal range")
        else:
            print(f" Found {len(anomalies)} anomalous results:\n")
            for i, anomaly in enumerate(anomalies, 1):
                print(f"{i}. {anomaly['timestamp']}")
                for issue in anomaly['issues']:
                    print(f"   - {issue}")
                print()
    
    elif args.machine:
        # Machine-specific stats
        print(f"\n{'='*60}")
        print(f"MACHINE STATISTICS - {args.machine}")
        print(f"{'='*60}\n")
        
        stats = aggregator.get_machine_stats(args.machine, args.hours)
        
        if 'error' in stats:
            print(f"Error: {stats['error']}")
            sys.exit(1)
        
        print(f"Period: Last {stats['period_hours']} hours")
        print(f"Tests: {stats['test_count']}")
        print(f"First Test: {stats['first_test']}")
        print(f"Last Test: {stats['last_test']}")
        
        print(f"\n{'Download Speed (Mbps)':-^60}")
        print(f"  Average:  {stats['download']['avg']:>8.2f}")
        print(f"  Median:   {stats['download']['median']:>8.2f}")
        print(f"  Min:      {stats['download']['min']:>8.2f}")
        print(f"  Max:      {stats['download']['max']:>8.2f}")
        print(f"  Std Dev:  {stats['download']['stdev']:>8.2f}")
        
        print(f"\n{'Upload Speed (Mbps)':-^60}")
        print(f"  Average:  {stats['upload']['avg']:>8.2f}")
        print(f"  Median:   {stats['upload']['median']:>8.2f}")
        print(f"  Min:      {stats['upload']['min']:>8.2f}")
        print(f"  Max:      {stats['upload']['max']:>8.2f}")
        print(f"  Std Dev:  {stats['upload']['stdev']:>8.2f}")
        
        print(f"\n{'Ping (ms)':-^60}")
        print(f"  Average:  {stats['ping']['avg']:>8.2f}")
        print(f"  Median:   {stats['ping']['median']:>8.2f}")
        print(f"  Min:      {stats['ping']['min']:>8.2f}")
        print(f"  Max:      {stats['ping']['max']:>8.2f}")
        print(f"  Std Dev:  {stats['ping']['stdev']:>8.2f}")
        
        if args.format == 'json':
            import json
            print(f"\n{'JSON Data':-^60}")
            print(json.dumps(stats, indent=2))
    
    elif args.comparison:
        # Comparison report
        print(f"\n{'='*60}")
        print(f"FLEET COMPARISON REPORT - Last {args.hours} Hours")
        print(f"{'='*60}\n")
        
        report = aggregator.get_comparison_report(args.hours)
        
        if not report.get('machines'):
            print("No speed test data available")
            sys.exit(0)
        
        print(f"Fleet Averages:")
        print(f"  Download: {report['fleet_avg_download']:.2f} Mbps")
        print(f"  Upload:   {report['fleet_avg_upload']:.2f} Mbps")
        print(f"  Ping:     {report['fleet_avg_ping']:.2f} ms")
        
        print(f"\n{'Machine Performance':-^60}")
        print(f"{'Machine':<20} {'Down':>8} {'Up':>8} {'Ping':>6} {'vs Fleet':>10} {'Tests':>6}")
        print(f"{'-'*60}")
        
        for machine in report['machines']:
            vs_fleet = f"{machine['download_vs_fleet']:+.1f}%"
            print(f"{machine['machine_id']:<20} "
                  f"{machine['avg_download']:>8.2f} "
                  f"{machine['avg_upload']:>8.2f} "
                  f"{machine['avg_ping']:>6.2f} "
                  f"{vs_fleet:>10} "
                  f"{machine['test_count']:>6}")
        
        if args.format == 'json':
            import json
            print(f"\n{'JSON Data':-^60}")
            print(json.dumps(report, indent=2))
    
    else:
        # Fleet summary
        report = aggregator.generate_report(format=args.format, hours=args.hours)
        print(report)


if __name__ == '__main__':
    main()
