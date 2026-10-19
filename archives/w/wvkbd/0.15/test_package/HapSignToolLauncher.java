// SPDX-License-Identifier: GPL-3.0-only
import java.io.DataInputStream;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.jar.Attributes;
import java.util.jar.JarFile;
import java.util.jar.Manifest;

/** Runs the local SDK signer with decrypted passwords passed over stdin. */
public final class HapSignToolLauncher {
    private static final String STORE_PASSWORD = "@WVKBD_STORE_PASSWORD@";
    private static final String KEY_PASSWORD = "@WVKBD_KEY_PASSWORD@";

    private static String readSecret(DataInputStream input) throws IOException {
        int length = input.readInt();
        if (length < 0 || length > 65536) {
            throw new IOException("invalid secret length");
        }
        byte[] bytes = input.readNBytes(length);
        if (bytes.length != length) {
            throw new IOException("incomplete secret input");
        }
        return new String(bytes, StandardCharsets.UTF_8);
    }

    public static void main(String[] args) {
        try {
            if (args.length < 2) {
                throw new IllegalArgumentException("missing signer invocation");
            }
            Path jarPath = Paths.get(args[0]).toAbsolutePath();
            int secretCount = Integer.parseInt(args[1]);
            if (secretCount != 0 && secretCount != 2) {
                throw new IllegalArgumentException("invalid secret count");
            }
            String storePassword = "";
            String keyPassword = "";
            if (secretCount == 2) {
                DataInputStream input = new DataInputStream(System.in);
                storePassword = readSecret(input);
                keyPassword = readSecret(input);
            }

            List<String> signerArgs = new ArrayList<>();
            for (int index = 2; index < args.length; index++) {
                String value = args[index];
                if (STORE_PASSWORD.equals(value)) {
                    value = storePassword;
                } else if (KEY_PASSWORD.equals(value)) {
                    value = keyPassword;
                }
                signerArgs.add(value);
            }

            try (JarFile jar = new JarFile(jarPath.toFile())) {
                Manifest manifest = jar.getManifest();
                if (manifest == null) {
                    throw new IOException("signer manifest missing");
                }
                String mainClass = manifest.getMainAttributes().getValue(Attributes.Name.MAIN_CLASS);
                if (mainClass == null || mainClass.isBlank()) {
                    throw new IOException("signer entry point missing");
                }
                List<URL> classPath = new ArrayList<>();
                classPath.add(jarPath.toUri().toURL());
                String dependencies = manifest.getMainAttributes().getValue(Attributes.Name.CLASS_PATH);
                if (dependencies != null) {
                    for (String dependency : dependencies.trim().split("\\s+")) {
                        if (!dependency.isEmpty()) {
                            classPath.add(jarPath.getParent().resolve(dependency).normalize().toUri().toURL());
                        }
                    }
                }
                try (URLClassLoader loader = new URLClassLoader(
                        classPath.toArray(new URL[0]), ClassLoader.getPlatformClassLoader())) {
                    Thread.currentThread().setContextClassLoader(loader);
                    Class<?> entry = Class.forName(mainClass, true, loader);
                    Method main = entry.getMethod("main", String[].class);
                    main.invoke(null, (Object) signerArgs.toArray(new String[0]));
                }
            }
        } catch (InvocationTargetException error) {
            System.err.println("SIGN_TOOL_FAILED");
            System.exit(1);
        } catch (Throwable error) {
            System.err.println("SIGN_LAUNCH_FAILED");
            System.exit(1);
        }
    }
}
