import server
import tornado.web


class RotateLogsHandler(tornado.web.RequestHandler):
    def get(self):
        server.logWriter.doRotateFiles()
        self.write('{"code": 0}')


settings = server.settings
settings.server_port = 15588
settings.log_directory = "test_directory"
settings.rotation_interval = -1 # means: do not rotate

server.handlers.append((r"/rotateLogs", RotateLogsHandler))

# to manually rotate "current" files
# server.application.add_handlers(".*$", [(r"/rotateLogs", RotateLogsHandler)])

if __name__ == "__main__":
    server.main()
