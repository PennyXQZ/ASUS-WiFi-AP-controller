import argparse
import asyncio # Allows asynchronous programming
import aiohttp # Handles HTTP requests (REST API, used by asusrouter)
import paramiko
from asusrouter import AsusRouter, AsusData
from asusrouter.modules.led import AsusLED
from asusrouter.modules.parental_control import AsusParentalControl
from asusrouter.modules.port_forwarding import AsusPortForwarding
from asusrouter.modules.system import AsusSystem
from asusrouter.modules.connection import ConnectionType, InternetMode

class AsusRouterController:
    def __init__(self, hostname, username, password, use_ssl=False, port=80):
        """Initialize the router controller."""
        self.hostname = hostname
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.port = port
        self.loop = None  # Create an event loop
        self.session = None
        self.router = None

    def connect_router(self):
        # Create a new event loop
        self.loop = asyncio.new_event_loop()  # Create an Async Event Loop, this loop manages all asynchronous tasks in the script

        # Create aiohttp session
        self.session = aiohttp.ClientSession(loop=self.loop) # Create an aiohttp Session
        
        #Creates an instance of AsusRouter to communicate with the Asus WiFi AP
        self.router = AsusRouter(
            hostname=self.hostname,     # Required - IP address of the router
            username=self.username,          # Required
            password=self.password,          # Required
            use_ssl=self.use_ssl,              # optional, makes sure connections are encrypted
            session=self.session,           # optional, uses the aiohttp session
            port=self.port,                   # Scan for open ports (command: 'nmap 10.150.4.2'), response '80/tcp   open  http', 80 is open for http, use http port here
        )

        # Connect to the router
        self.loop.run_until_complete(self.router.async_connect()) 
        # 'router.async_connect() ' logs into the router and establishes a session 
        # 'run_until_complete()' ensures the async task completes before moving to the next line


    def disconnect_router(self):
        # disconnect and close the session when you're done
        try:
            self.loop.run_until_complete(self.router.async_disconnect()) # logs out of the router
        except Exception as e:
            print(f"Error disconnecting router: {e}") 
        finally:  
            self.loop.run_until_complete(self.session.close()) #closes the HTTP session, releasing resources
        
    def query_data(self, data_type):
        router_controller.connect_router()
        try:
            if hasattr(AsusData, data_type.upper()):
                data = self.loop.run_until_complete(self.router.async_get_data(getattr(AsusData, data_type.upper()))) # fetches network-related information from the router
                print(f"{data_type}: {data}")
            else:
                print(f"Invalid data type '{data_type}'. Available options: {', '.join([attr for attr in dir(AsusData) if not attr.startswith('__')])}")
        except Exception as e:
            print(f"Could not fetch {data_type}: {e}")
        router_controller.disconnect_router()


    def turn_LED(self, state):
        router_controller.disconnect_router()
        try:
            if hasattr(AsusLED,state.upper()):
                self.loop.run_until_complete(self.router.async_set_state(getattr(AsusLED,state.upper())))
                print(f"LED Turned {state.upper()}")
                self.query_data(data_type="LED")
            else:
                print("Invalid LED state. Use 'on' or 'off'.")
        except Exception as e:
            print(f"Error setting LED state: {e}")
        router_controller.connect_router()

    def reboot_ap(self):
        router_controller.connect_router()
        try:
            self.loop.run_until_complete(self.router.async_set_state(AsusSystem.REBOOT))
            print(f"The AP has been rebooted")
        except Exception as e:
            print(f"Error to reboot: {e}")
        router_controller.disconnect_router()

    def nvram_show(self, param):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=self.hostname, username=self.username, password=self.password)
            
            if param is not None:
                stdin, stdout, stderr = ssh.exec_command(f'nvram get {param}')
            else:
                stdin, stdout, stderr = ssh.exec_command('nvram show')

            output = stdout.read().decode('utf-8')  # Read command output
            error = stderr.read().decode('utf-8')  # Read errors if any

            ssh.close()  # Close SSH connection

            print(f'The value of {param} is {output}')

            if error:
                return f"Error: {error.strip()}"
            return output.strip()

        except Exception as e:
            print(f"Error for nvram command: {e}")
    
    def nvram_set(self, param, value):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=self.hostname, username=self.username, password=self.password)
            
            if param is not None and value is not None:
                command = f'nvram set {param}="{value}"'
                stdin, stdout, stderr = ssh.exec_command(command)
            else:
                print(f'The paramter and its value have to be set')

            output = stdout.read().decode('utf-8')  # Read command output
            error = stderr.read().decode('utf-8')  # Read errors if any

            ssh.exec_command("nvram commit")
            ssh.exec_command("nvram save")
            self.nvram_show(param)

            ssh.close()  # Close SSH connection

            if error:
                return f"Error: {error.strip()}"
            return output.strip()

        except Exception as e:
            print(f"Error for nvram command: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Control Asus Router via CLI")
    
    # **Required command argument**
    parser.add_argument("--command", choices={"query_data","turn_led", "reboot", "nvram_set", "nvram_show"}, default="nvram_set", help="Command to execute")
    # **Optional arguments for commands that need input**
    parser.add_argument("--data_type", type=str, required=False, default="PORTS",help="Specify which router data to fetch (e.g., AIMESH, BOOTTIME, CLIENTS, CPU, DEVICEMAP, FIRMWARE, GWLAN, LED, NETWORK, NODE_INFO, OPENVPN_CLIENT, OPENVPN_SERVER, PARENTAL_CONTROL, PORT_FORWARDING, PORTS, RAM, SYSINFO, TEMPERATURE, VPNC, VPNC_CLIENTLIST, WAN, WIREGUARD_CLIENT, WIREGUARD_SERVER, WLAN)")
    parser.add_argument("--state", choices= {"on", "off"}, default="off", help="Set state for LED")
    parser.add_argument("--nvram_param", type=str, required=False, default="wl1_txpower", help="Specify the nvram paramer to be set")
    parser.add_argument("--nvram_value", type=float, required=False, default="80", help="Specify value to be set for the nvram parameter")

    args = parser.parse_args()


    router_controller = AsusRouterController(
        hostname="10.150.4.2",     # Required - IP address of the router
        username="ncomm",          # Required
        password="ncomm",          # Required
        use_ssl=False,             # optional, makes sure connections are encrypted
        port=80                   # Scan for open ports (command: 'nmap 10.150.4.2'), response '80/tcp   open  http', 80 is open for http, use http port here
    )



    if args.command == "query_data":
        router_controller.query_data(args.data_type)
    elif args.command == "turn_led":
        router_controller.turn_LED(args.state)
    elif args.command == "reboot":
        router_controller.reboot_ap()
    elif args.command == "nvram_show":
        router_controller.nvram_show(args.nvram_param)
    elif args.command == "nvram_set":
        router_controller.nvram_set(args.nvram_param,args.nvram_value)




