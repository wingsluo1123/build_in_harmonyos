<?php
/**
 * test_package consumer test for wallabag/2.6.14 (R34: real API usage).
 *
 * Usage: php test_wallabag.php <share-dir>
 *
 * Exercises the packaged bundle for real: parses the shipped version file,
 * boots the composer autoloader, loads a genuine wallabag class and calls its
 * methods. Every check() call is one counted assertion; the final line is the
 * single deterministic source for HMBS_TEST_PACKAGE_RESULT counts (no
 * stdout word-counting anywhere).
 */
$share = isset($argv[1]) ? $argv[1] : '';
$total = 0;
$passed = 0;

function check($name, $cond) {
    global $total, $passed;
    $total++;
    if ($cond) {
        $passed++;
        echo "[ok] $name\n";
    } else {
        echo "[FAIL] $name\n";
    }
}

check('share dir exists', is_dir($share));

$ymlPath = $share . '/app/config/wallabag.yml';
$yml = is_file($ymlPath) ? file_get_contents($ymlPath) : false;
check('wallabag.yml exists with version 2.6.14',
    $yml !== false && strpos($yml, 'version: 2.6.14') !== false);

$autoloadPath = $share . '/vendor/autoload.php';
check('vendor/autoload.php exists', is_file($autoloadPath));

$loader = require $autoloadPath;
check('autoloader boots (ClassLoader instance)',
    is_object($loader) && $loader instanceof Composer\Autoload\ClassLoader);

check('class Wallabag\\CoreBundle\\Tools\\Utils loads',
    class_exists('Wallabag\\CoreBundle\\Tools\\Utils'));

check('Utils::DEFAULT_WORDS_PER_MINUTE === 200',
    Wallabag\CoreBundle\Tools\Utils::DEFAULT_WORDS_PER_MINUTE === 200);

$token = Wallabag\CoreBundle\Tools\Utils::generateToken(15);
check('Utils::generateToken(15) returns url-safe token',
    is_string($token) && strlen($token) > 0 && strlen($token) <= 15
    && strpos($token, '+') === false && strpos($token, '/') === false);

$readingTime = Wallabag\CoreBundle\Tools\Utils::getReadingTime('hello world');
check('Utils::getReadingTime executes (float result)',
    is_float($readingTime) && $readingTime >= 0);

check('bin/console entrypoint exists', is_file($share . '/bin/console'));
check('app/config/parameters.yml exists',
    is_file($share . '/app/config/parameters.yml'));

// Negative controls: unknown classes must NOT load, and the harness itself
// must be able to observe a PHP failure (toybox lesson: a harness that can
// never fail proves nothing).
check('negative: unknown class does not exist',
    class_exists('Wallabag\\DoesNotExist\\Nope') === false);

$harnessCatchesFailure = false;
try {
    eval('function __wallabag_broken_probe() {{');
} catch (ParseError $e) {
    $harnessCatchesFailure = true;
}
check('negative: harness observes ParseError', $harnessCatchesFailure === true);

$ok = ($passed === $total);
$marker = array(
    'executed' => true,
    'passed' => $ok,
    'command' => 'php test_wallabag.php <share-dir>',
    'discovered' => $total,
    'passedCount' => $passed,
);
echo 'HMBS_TEST_PACKAGE_RESULT=' . json_encode($marker) . "\n";
exit($ok ? 0 : 1);
