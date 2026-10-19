import os
import subprocess
import psutil
import datetime
import json
from pathlib import Path
import shutil
import concurrent.futures
import threading
from collections import defaultdict

class VPSSpeedOptimizer:
    def __init__(self, silent=False):
        self.silent = silent
        self.report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'health_score': 0,
            'issues': [],
            'recommendations': [],
            'cleaned_items': [],
            'system_info': {},
            'performance_gains': []
        }

    def log(self, message):
        """In thông báo nếu không ở chế độ silent"""
        if not self.silent:
            print(message)

    def get_system_info_fast(self):
        """Thu thập thông tin hệ thống nhanh chóng"""
        try:
            # Sử dụng threading để thu thập song song
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                cpu_future = executor.submit(self._get_cpu_info)
                memory_future = executor.submit(self._get_memory_info)
                disk_future = executor.submit(self._get_disk_info)
                network_future = executor.submit(self._get_network_info)

                self.report['system_info'] = {
                    'cpu': cpu_future.result(),
                    'memory': memory_future.result(),
                    'disk': disk_future.result(),
                    'network': network_future.result(),
                    'uptime': self._get_uptime()
                }

            self.log("✓ Thu thập thông tin hệ thống hoàn tất")

        except Exception as e:
            self.log(f"✗ Lỗi thu thập thông tin: {e}")

    def _get_cpu_info(self):
        """Lấy thông tin CPU"""
        return {
            'cores': psutil.cpu_count(),
            'usage': psutil.cpu_percent(interval=0.1),  # Giảm thời gian chờ
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }

    def _get_memory_info(self):
        """Lấy thông tin RAM"""
        memory = psutil.virtual_memory()
        return {
            'total_gb': round(memory.total / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'usage_percent': memory.percent
        }

    def _get_disk_info(self):
        """Lấy thông tin ổ đĩa"""
        disk = psutil.disk_usage('/')
        return {
            'total_gb': round(disk.total / (1024**3), 2),
            'used_gb': round(disk.used / (1024**3), 2),
            'free_gb': round(disk.free / (1024**3), 2),
            'usage_percent': round((disk.used / disk.total) * 100, 2)
        }

    def _get_network_info(self):
        """Lấy thông tin network"""
        network = psutil.net_io_counters()
        return {
            'bytes_sent_gb': round(network.bytes_sent / (1024**3), 2),
            'bytes_recv_gb': round(network.bytes_recv / (1024**3), 2)
        }

    def _get_uptime(self):
        """Lấy uptime"""
        try:
            uptime_seconds = psutil.boot_time()
            uptime_hours = (datetime.datetime.now().timestamp() - uptime_seconds) / 3600
            return f"{uptime_hours:.1f}h"
        except:
            return "N/A"

    def aggressive_log_cleanup(self):
        """Dọn dẹp log files một cách tích cực"""
        cleaned_items = []
        cleaned_size = 0

        # Các thư mục log chính
        log_locations = [
            '/var/log',
            '/var/log/nginx',
            '/var/log/apache2',
            '/var/log/mysql',
            '/var/log/postgresql',
            '/var/log/redis',
            '/var/log/mongodb',
            '/home/*/logs',
            '/opt/*/logs',
            '/usr/local/*/logs'
        ]

        def cleanup_log_dir(log_path):
            items_cleaned = []
            size_freed = 0

            if not os.path.exists(log_path):
                return items_cleaned, size_freed

            try:
                # Xóa log files cũ hơn 3 ngày
                result = subprocess.run([
                    'find', log_path, '-type', 'f', 
                    '(', '-name', '*.log', '-o', '-name', '*.log.*', ')', 
                    '-mtime', '+3', '-ls', '-delete'
                ], capture_output=True, text=True, timeout=30)

                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            # Tính size từ output của find -ls
                            parts = line.split()
                            if len(parts) > 6:
                                try:
                                    size_freed += int(parts[6])
                                except:
                                    pass
                    items_cleaned.append(f"Xóa log files cũ trong {log_path}")

                # Làm trống log files hiện tại lớn hơn 100MB
                result = subprocess.run([
                    'find', log_path, '-type', 'f', '-name', '*.log',
                    '-size', '+100M', '-exec', 'truncate', '-s', '0', '{}', ';'
                ], capture_output=True, timeout=30)

                if result.returncode == 0:
                    items_cleaned.append(f"Làm trống log files lớn trong {log_path}")

            except Exception as e:
                if not self.silent:
                    print(f"Lỗi dọn dẹp {log_path}: {e}")

            return items_cleaned, size_freed

        # Dọn dẹp song song
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            for log_path in log_locations:
                future = executor.submit(cleanup_log_dir, log_path)
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                items, size = future.result()
                cleaned_items.extend(items)
                cleaned_size += size

        # Dọn dẹp journald logs
        try:
            subprocess.run(['journalctl', '--vacuum-time=7d'], 
                         capture_output=True, timeout=30)
            cleaned_items.append("Dọn dẹp journald logs (>7 ngày)")
        except:
            pass

        self.report['performance_gains'].append(
            f"Giải phóng {cleaned_size / (1024**2):.1f}MB từ log files"
        )

        return cleaned_items

    def turbo_temp_cleanup(self):
        """Dọn dẹp file tạm siêu nhanh"""
        cleaned_items = []

        # Các thư mục temp
        temp_locations = [
            '/tmp',
            '/var/tmp', 
            '/var/cache',
            '/var/spool/tmp',
            '/usr/tmp',
            '/home/*/tmp',
            '/home/*/.cache'
        ]

        def clean_temp_location(temp_path):
            try:
                if not os.path.exists(temp_path):
                    return []

                # Xóa files cũ hơn 1 ngày
                subprocess.run([
                    'find', temp_path, '-type', 'f', '-mtime', '+1', '-delete'
                ], capture_output=True, timeout=20)

                # Xóa thư mục trống
                subprocess.run([
                    'find', temp_path, '-type', 'd', '-empty', '-delete'
                ], capture_output=True, timeout=20)

                return [f"Dọn dẹp {temp_path}"]

            except Exception:
                return []

        # Dọn dẹp song song
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(clean_temp_location, path) 
                      for path in temp_locations]

            for future in concurrent.futures.as_completed(futures):
                cleaned_items.extend(future.result())

        return cleaned_items

    def extreme_package_cleanup(self):
        """Dọn dẹp package cache tích cực"""
        cleaned_items = []

        cleanup_commands = []

        # Ubuntu/Debian
        if shutil.which('apt'):
            cleanup_commands.extend([
                (['apt', 'autoremove', '-y'], "APT autoremove"),
                (['apt', 'autoclean'], "APT autoclean"),
                (['apt', 'clean'], "APT clean"),
            ])

        # CentOS/RHEL/Fedora
        if shutil.which('yum'):
            cleanup_commands.extend([
                (['yum', 'autoremove', '-y'], "YUM autoremove"),
                (['yum', 'clean', 'all'], "YUM clean all"),
            ])

        if shutil.which('dnf'):
            cleanup_commands.extend([
                (['dnf', 'autoremove', '-y'], "DNF autoremove"),
                (['dnf', 'clean', 'all'], "DNF clean all"),
            ])

        # Docker cleanup
        if shutil.which('docker'):
            cleanup_commands.extend([
                (['docker', 'system', 'prune', '-af'], "Docker system prune"),
                (['docker', 'volume', 'prune', '-f'], "Docker volume prune"),
                (['docker', 'network', 'prune', '-f'], "Docker network prune"),
            ])

        # Snap cleanup
        if shutil.which('snap'):
            cleanup_commands.append(
                (['snap', 'refresh'], "Snap refresh")
            )

        # Thực hiện song song
        def run_cleanup_command(cmd_info):
            cmd, description = cmd_info
            try:
                result = subprocess.run(cmd, capture_output=True, 
                                      text=True, timeout=60)
                if result.returncode == 0:
                    return f"✓ {description}"
                else:
                    return f"⚠ {description} (có cảnh báo)"
            except Exception:
                return f"✗ {description} (thất bại)"

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_cleanup_command, cmd) 
                      for cmd in cleanup_commands]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                cleaned_items.append(result)

        return cleaned_items

    def memory_optimization(self):
        """Tối ưu hóa memory"""
        optimizations = []

        try:
            # Drop caches
            with open('/proc/sys/vm/drop_caches', 'w') as f:
                f.write('3')
            optimizations.append("✓ Cleared system caches")

            # Compact memory
            try:
                with open('/proc/sys/vm/compact_memory', 'w') as f:
                    f.write('1')
                optimizations.append("✓ Compacted memory")
            except:
                pass

            # Sync filesystem
            subprocess.run(['sync'], timeout=10)
            optimizations.append("✓ Synchronized filesystems")

        except Exception as e:
            optimizations.append(f"⚠ Memory optimization error: {e}")

        return optimizations

    def process_optimization(self):
        """Tối ưu hóa processes"""
        optimizations = []

        try:
            # Kill zombie processes
            zombies = []
            for proc in psutil.process_iter(['pid', 'status']):
                try:
                    if proc.info['status'] == psutil.STATUS_ZOMBIE:
                        zombies.append(proc.info['pid'])
                except:
                    pass

            if zombies:
                for pid in zombies:
                    try:
                        os.kill(pid, 9)
                    except:
                        pass
                optimizations.append(f"✓ Killed {len(zombies)} zombie processes")

            # Optimize swappiness (nếu có quyền)
            try:
                with open('/proc/sys/vm/swappiness', 'w') as f:
                    f.write('10')
                optimizations.append("✓ Optimized swappiness to 10")
            except:
                pass

        except Exception as e:
            optimizations.append(f"⚠ Process optimization error: {e}")

        return optimizations

    def network_optimization(self):
        """Tối ưu hóa network"""
        optimizations = []

        try:
            # Flush DNS cache
            dns_commands = [
                (['systemctl', 'flush-dns'], "SystemD DNS flush"),
                (['resolvectl', 'flush-caches'], "Resolve flush"),
                (['systemctl', 'restart', 'systemd-resolved'], "Restart DNS resolver")
            ]

            for cmd, desc in dns_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=10)
                    if result.returncode == 0:
                        optimizations.append(f"✓ {desc}")
                        break
                except:
                    continue

        except Exception as e:
            optimizations.append(f"⚠ Network optimization error: {e}")

        return optimizations

    def turbo_cleanup(self):
        """Thực hiện dọn dẹp turbo"""
        self.log("🚀 Bắt đầu dọn dẹp TURBO MODE...")

        cleaned_items = []

        # Chạy tất cả các cleanup tasks song song
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # Submit all cleanup tasks
            log_future = executor.submit(self.aggressive_log_cleanup)
            temp_future = executor.submit(self.turbo_temp_cleanup)
            package_future = executor.submit(self.extreme_package_cleanup)
            memory_future = executor.submit(self.memory_optimization)
            process_future = executor.submit(self.process_optimization)
            network_future = executor.submit(self.network_optimization)

            # Collect results
            try:
                cleaned_items.extend(log_future.result(timeout=120))
                cleaned_items.extend(temp_future.result(timeout=60))
                cleaned_items.extend(package_future.result(timeout=180))
                cleaned_items.extend(memory_future.result(timeout=30))
                cleaned_items.extend(process_future.result(timeout=30))
                cleaned_items.extend(network_future.result(timeout=30))
            except Exception as e:
                self.log(f"⚠ Một số tác vụ không hoàn thành: {e}")

        self.report['cleaned_items'] = cleaned_items
        self.log(f"✅ TURBO cleanup hoàn thành - {len(cleaned_items)} tác vụ")

        return cleaned_items

    def speed_check(self):
        """Kiểm tra tốc độ hệ thống"""
        checks = []
        health_score = 100

        sys_info = self.report['system_info']

        # CPU check
        cpu_usage = sys_info['cpu']['usage']
        if cpu_usage > 80:
            health_score -= 20
            checks.append(f"❌ CPU cao: {cpu_usage}%")
        elif cpu_usage > 60:
            health_score -= 10
            checks.append(f"⚠ CPU: {cpu_usage}%")
        else:
            checks.append(f"✅ CPU tốt: {cpu_usage}%")

        # Memory check
        mem_usage = sys_info['memory']['usage_percent']
        if mem_usage > 85:
            health_score -= 25
            checks.append(f"❌ RAM cao: {mem_usage}%")
        elif mem_usage > 70:
            health_score -= 15
            checks.append(f"⚠ RAM: {mem_usage}%")
        else:
            checks.append(f"✅ RAM tốt: {mem_usage}%")

        # Disk check
        disk_usage = sys_info['disk']['usage_percent']
        if disk_usage > 90:
            health_score -= 30
            checks.append(f"❌ Disk đầy: {disk_usage}%")
        elif disk_usage > 80:
            health_score -= 15
            checks.append(f"⚠ Disk: {disk_usage}%")
        else:
            checks.append(f"✅ Disk tốt: {disk_usage}%")

        self.report['health_score'] = max(0, health_score)
        self.report['issues'] = [check for check in checks if '❌' in check or '⚠' in check]

        return checks

    def generate_speed_report(self):
        """Tạo báo cáo tốc độ"""
        if not self.silent:
            print("\n" + "🚀" + "="*50)
            print("⚡ VPS SPEED OPTIMIZER REPORT")
            print("="*52)

            # Health score
            score = self.report['health_score']
            if score >= 90:
                status = "🟢 EXCELLENT"
            elif score >= 75:
                status = "🟡 GOOD"  
            elif score >= 50:
                status = "🟠 NEEDS ATTENTION"
            else:
                status = "🔴 CRITICAL"

            print(f"📊 Performance Score: {score}/100 - {status}")

            # System info
            sys_info = self.report['system_info']
            print(f"💻 CPU: {sys_info['cpu']['usage']}% | "
                  f"RAM: {sys_info['memory']['usage_percent']}% | "
                  f"Disk: {sys_info['disk']['usage_percent']}%")

            # Performance gains
            if self.report['performance_gains']:
                print("\n⚡ PERFORMANCE GAINS:")
                for gain in self.report['performance_gains']:
                    print(f"  • {gain}")

            # Cleaned items (show only count for speed)
            if self.report['cleaned_items']:
                print(f"\n🧹 OPTIMIZATIONS: {len(self.report['cleaned_items'])} tasks completed")

            print("="*52)

    def run_speed_optimization(self):
        """Chạy tối ưu hóa tốc độ"""
        start_time = datetime.datetime.now()

        self.log("⚡ VPS SPEED OPTIMIZER STARTING...")

        try:
            # Thu thập thông tin nhanh
            self.get_system_info_fast()

            # Kiểm tra tốc độ
            self.speed_check()

            # Thực hiện tối ưu hóa
            self.turbo_cleanup()

            # Tạo báo cáo
            self.generate_speed_report()

            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.log(f"⚡ Hoàn thành trong {duration:.1f} giây")

        except Exception as e:
            self.log(f"❌ Lỗi: {e}")
            raise

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='VPS Speed Optimizer - Tối ưu tốc độ VPS')
    parser.add_argument('--silent', action='store_true', help='Chế độ im lặng')
    parser.add_argument('--logs-only', action='store_true', help='Chỉ dọn log files')
    parser.add_argument('--memory-only', action='store_true', help='Chỉ tối ưu memory')
    parser.add_argument('--check-only', action='store_true', help='Chỉ kiểm tra, không cleanup')

    args = parser.parse_args()

    optimizer = VPSSpeedOptimizer(silent=args.silent)

    try:
        if args.logs_only:
            optimizer.get_system_info_fast()
            optimizer.aggressive_log_cleanup()
            optimizer.generate_speed_report()
        elif args.memory_only:
            optimizer.get_system_info_fast()
            optimizer.memory_optimization()
            optimizer.generate_speed_report()
        elif args.check_only:
            optimizer.get_system_info_fast()
            optimizer.speed_check()
            optimizer.generate_speed_report()
        else:
            optimizer.run_speed_optimization()

    except KeyboardInterrupt:
        print("\n⚠️ Đã hủy bởi người dùng")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    main()
