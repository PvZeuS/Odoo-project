pipeline {
    agent any

    environment {
        EC2_USER       = 'ubuntu'
        EC2_IP         = branchIP()
        REMOTE_DIR     = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        POSTGRES_DB    = "db_${env.BRANCH_NAME}"
        ODOO_PORT      = branchPort()
        COMPOSE_PROJECT_NAME = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        DB_PASS_CRED   = credentials('odoo-db-password')
    }

    stages {
        stage('Workspace Cleanup') {
            steps {
                deleteDir()
                checkout scm
            }
        }

        stage('Disk Maintenance') {
            steps {
                sh 'docker system prune -f --volumes'
            }
        }

        stage('Linting') {
            steps {
                echo "--- Analizando código con Flake8 (Local) ---"
                // Instalamos y corremos flake8 directamente en el agente para evitar problemas de volúmenes Docker
                sh """
                    pip install flake8 --break-system-packages || pip install flake8
                    if [ -d './addons' ]; then
                        flake8 ./addons --count --select=E9,F63,F7,F82 --show-source --statistics
                    else
                        echo "ADVERTENCIA: No se encontró carpeta addons, saltando linting."
                    fi
                """
            }
        }

        stage('Smart Unit Tests') {
            steps {
                script {
                    def commitMsg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    def targetModule = getTargetModule(commitMsg)
                    
                    if (targetModule) {
                        echo "--- EJECUTANDO TESTS PARA: ${targetModule} ---"
                        withEnv(["DB_PASS=${DB_PASS_CRED}"]) {
                            sh """
                                docker network create test-net-${BUILD_NUMBER} || true
                                
                                docker run -d --name db-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    -e POSTGRES_PASSWORD=\$DB_PASS -e POSTGRES_USER=odoo -e POSTGRES_DB=postgres \
                                    postgres:16-alpine
                                
                                sleep 15

                                # Corremos el test SIN --volumes-from para evitar el error de ruta
                                # Copiamos los archivos directamente al contenedor de test
                                docker run -d --name odoo-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    -e PGPASSWORD=\$DB_PASS \
                                    odoo:19.0 tail -f /dev/null

                                docker cp ./addons odoo-test-${BUILD_NUMBER}:/var/lib/odoo/addons/19.0/custom_addons
                                
                                docker exec -u root odoo-test-${BUILD_NUMBER} sh -c "
                                    pip install --break-system-packages websocket-client && \
                                    odoo -d odoo_test \
                                    --db_host db-test-${BUILD_NUMBER} \
                                    --db_user odoo \
                                    --db_password=\$DB_PASS \
                                    --addons-path=/var/lib/odoo/addons/19.0/custom_addons \
                                    -i ${targetModule} --test-enable --stop-after-init --log-level=test --test-tags /${targetModule}
                                "
                            """
                        }
                    } else {
                        echo "--- SALTANDO TESTS ---"
                    }
                }
            }
            post {
                always {
                    sh "docker stop odoo-test-${BUILD_NUMBER} || true && docker rm odoo-test-${BUILD_NUMBER} || true"
                    sh "docker stop db-test-${BUILD_NUMBER} || true && docker rm db-test-${BUILD_NUMBER} || true"
                    sh "docker network rm test-net-${BUILD_NUMBER} || true"
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent(['ec2-odoo-key']) { 
                    withEnv(["TARGET_DB_PASS=${DB_PASS_CRED}"]) {
                        sh """
                            echo "Preparando despliegue en ${EC2_IP}..."
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                            scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                            
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << EOF
                                cd ${REMOTE_DIR}
                                echo 'POSTGRES_PASSWORD=${TARGET_DB_PASS}' > .env
                                echo 'ODOO_PORT=${ODOO_PORT}' >> .env
                                echo 'COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}' >> .env
                                
                                if [ -f "./config/odoo.conf" ]; then
                                    sed -i 's/^db_password =.*/db_password = ${TARGET_DB_PASS}/' ./config/odoo.conf
                                fi
                                
                                docker compose down --remove-orphans
                                docker compose up -d
                                sleep 20
                                
                                CONTAINER_ID=\\\$(docker compose ps -q odoo)
                                STATUS=\\\$(docker inspect -f '{{.State.Status}}' \\\$CONTAINER_ID)
                                
                                if [ "\\\$STATUS" != "running" ]; then
                                    docker compose logs --tail=50 odoo
                                    exit 1
                                fi

                                docker compose exec -T -e PGPASSWORD='${TARGET_DB_PASS}' odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init --no-http
EOF
                        """
                    }
                }
            }
        }
    }

    post {
        success { echo "--- DESPLIEGUE OK EN ${env.BRANCH_NAME.toUpperCase()} ---" }
        failure { echo "--- PIPELINE FALLIDO ---" }
    }
}

@NonCPS
def getTargetModule(String msg) {
    def match = (msg =~ /MOD:([a-zA-Z0-9_]+)/)
    return match ? match[0][1] : null
}

def branchIP() { 
    return (env.BRANCH_NAME == 'main') ? '3.144.231.64' : '18.219.33.101' 
}

def branchPort() { 
    return (env.BRANCH_NAME == 'main') ? '8071' : '8070' 
}