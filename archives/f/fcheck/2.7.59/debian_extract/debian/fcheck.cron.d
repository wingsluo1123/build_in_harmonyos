#
# Regular cron job for the fcheck package
#
30 */2	* * *	root	test -x /usr/sbin/fcheck && if ! nice ionice -c3 /usr/sbin/fcheck -asxrf /etc/fcheck/fcheck.cfg >/var/run/fcheck.out 2>&1; then mailx -s "ALERT: [fcheck] `hostname --fqdn`" root </var/run/fcheck.out ; /usr/sbin/fcheck -cadsxlf /etc/fcheck/fcheck.cfg ; fi ; rm -f /var/run/fcheck.out
