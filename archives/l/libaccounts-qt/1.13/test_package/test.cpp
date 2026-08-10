#include <Accounts/Manager>
#include <cstdio>

int main(void) {
    // Test that we can create an Accounts::Manager object
    Accounts::Manager *manager = new Accounts::Manager();
    if (manager == nullptr) {
        fprintf(stderr, "Failed to create Accounts::Manager\n");
        return 1;
    }
    printf("libaccounts-qt test: Manager created successfully\n");
    delete manager;
    printf("libaccounts-qt test passed\n");
    return 0;
}
