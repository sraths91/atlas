"""
Fleet Certificate Auto-Renewal Service
Automatically renews Let's Encrypt certificates before expiration
"""

import sys
import time
import logging
import schedule
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    from .fleet_letsencrypt import LetsEncryptManager, ACME_AVAILABLE
except ImportError:
    from fleet_letsencrypt import LetsEncryptManager, ACME_AVAILABLE


class CertificateRenewalService:
    """Automatic certificate renewal service"""
    
    def __init__(self, domain: str, webroot_path: str, email: str, 
                 staging: bool = False, check_interval_hours: int = 12):
        """
        Initialize renewal service
        
        Args:
            domain: Domain name for certificate
            webroot_path: Path for HTTP-01 challenge
            email: Contact email
            staging: Use Let's Encrypt staging
            check_interval_hours: How often to check for renewal (default: 12 hours)
        """
        self.domain = domain
        self.webroot_path = webroot_path
        self.email = email
        self.staging = staging
        self.check_interval_hours = check_interval_hours
        
        self.manager = LetsEncryptManager(staging=staging)
        self.running = False
    
    def check_and_renew(self):
        """Check if renewal is needed and renew if necessary"""
        try:
            logger.info("Checking certificate expiration...")
            
            expiration = self.manager.check_expiration()
            if expiration is None:
                logger.warning("No certificate found, obtaining new one...")
                self._obtain_initial_certificate()
                return
            
            days_until_expiry = (expiration - datetime.now()).days
            logger.info(f"Certificate expires in {days_until_expiry} days ({expiration})")
            
            # Renew if expiring within 30 days
            if self.manager.needs_renewal(days_before=30):
                logger.info("Certificate needs renewal, starting renewal process...")
                
                if self.manager.renew_certificate(self.domain, self.webroot_path):
                    logger.info("Certificate renewed successfully!")
                    self._notify_server_reload()
                else:
                    logger.error("Certificate renewal failed!")
            else:
                logger.info("Certificate is still valid, no renewal needed")
                
        except Exception as e:
            logger.error(f"Error during renewal check: {e}", exc_info=True)
    
    def _obtain_initial_certificate(self):
        """Obtain initial certificate"""
        logger.info("Obtaining initial certificate...")
        
        # Register account if needed
        if not self.manager.account_key_path.exists():
            logger.info("Registering Let's Encrypt account...")
            if not self.manager.register_account(self.email):
                logger.error("Failed to register account")
                return
        
        # Obtain certificate
        if self.manager.obtain_certificate(self.domain, self.webroot_path):
            logger.info("Initial certificate obtained!")
            self._notify_server_reload()
        else:
            logger.error("Failed to obtain initial certificate")
    
    def _notify_server_reload(self):
        """Notify Fleet server to reload certificate"""
        try:
            # Try to send signal to server process
            import signal
            import psutil
            
            # Find fleet_server process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and 'fleet_server' in ' '.join(cmdline):
                        logger.info(f"Sending SIGHUP to fleet_server (PID: {proc.info['pid']})")
                        os.kill(proc.info['pid'], signal.SIGHUP)
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            logger.warning("Could not find fleet_server process to reload")
            
        except ImportError:
            logger.warning("psutil not available, cannot auto-reload server")
        except Exception as e:
            logger.error(f"Error notifying server: {e}")
    
    def start(self):
        """Start the renewal service"""
        if not ACME_AVAILABLE:
            logger.error("ACME libraries not available, cannot start renewal service")
            return
        
        logger.info(f"Starting certificate renewal service for {self.domain}")
        logger.info(f"Checking every {self.check_interval_hours} hours")
        logger.info(f"Webroot: {self.webroot_path}")
        logger.info(f"Staging: {self.staging}")
        
        # Initial check
        self.check_and_renew()
        
        # Schedule periodic checks
        schedule.every(self.check_interval_hours).hours.do(self.check_and_renew)
        
        # Also check daily at 3 AM
        schedule.every().day.at("03:00").do(self.check_and_renew)
        
        self.running = True
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute for scheduled tasks
        except KeyboardInterrupt:
            logger.info("Renewal service stopped by user")
        except Exception as e:
            logger.error(f"Renewal service error: {e}", exc_info=True)
    
    def stop(self):
        """Stop the renewal service"""
        logger.info("Stopping renewal service...")
        self.running = False


def run_renewal_service():
    """Run renewal service from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fleet Certificate Auto-Renewal Service')
    parser.add_argument('--domain', required=True, help='Domain name')
    parser.add_argument('--webroot', required=True, help='Webroot path for HTTP challenge')
    parser.add_argument('--email', required=True, help='Contact email')
    parser.add_argument('--staging', action='store_true', help='Use Let\'s Encrypt staging')
    parser.add_argument('--interval', type=int, default=12, help='Check interval in hours (default: 12)')
    parser.add_argument('--check-now', action='store_true', help='Check and renew immediately, then exit')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(Path.home() / 'Library' / 'Logs' / 'fleet_cert_renewal.log')),
            logging.StreamHandler()
        ]
    )
    
    service = CertificateRenewalService(
        domain=args.domain,
        webroot_path=args.webroot,
        email=args.email,
        staging=args.staging,
        check_interval_hours=args.interval
    )
    
    if args.check_now:
        # One-time check and exit
        service.check_and_renew()
    else:
        # Run as service
        service.start()


if __name__ == '__main__':
    run_renewal_service()
