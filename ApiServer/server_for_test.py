import server
import tornado.web


settings = server.settings
settings.server_port = 15588


if __name__ == "__main__":
    server.main()
