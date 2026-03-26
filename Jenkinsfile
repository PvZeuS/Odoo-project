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
        stage('Disk Maintenance') {
            steps {
                sh 'docker system prune -f --volumes'
            }
        }

        stage('Linting & Static Analysis') {
            steps {
                echo "--- Analizando código con Flake8 ---"
                sh """
                    docker run --rm \
                        -v ${env.WORKSPACE}:/apps \
                        -w /apps \
                        python:3.12-slim sh -c "
                            pip install flake8 && \
                            if [ -d './addons' ]; then \
                                flake8 ./addons --count --select=E9,F63,F7,F82 --show-source --statistics && \
                                flake8 ./addons --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics; \
                            else \
                                echo 'ERROR: No se encuentra la carpeta ./addons en el workspace'; \
                                ls -R /apps; \
                                exit 1; \
                            fi
                        "
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
                        def jenkinsID = sh(script: 'hostname', returnStdout: true).trim()
                        
                        withEnv(["DB_PASS=${DB_PASS_CRED}"]) {
                            sh """
                                docker network create test-net-${BUILD_NUMBER} || true
                                
                                docker run -d --name db-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    -e POSTGRES_PASSWORD=\$DB_PASS -e POSTGRES_USER=odoo -e POSTGRES_DB=postgres \
                                    postgres:16-alpine
                                
                                sleep 15

                                docker run --rm --name odoo-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    --volumes-from ${jenkinsID} \
                                    --user root \
                                    odoo:19.0 sh -c "
                                        pip install --break-system-packages websocket-client && \
                                        odoo -d odoo_test \
                                        --db_host db-test-${BUILD_NUMBER} \
                                        --db_user odoo \
                                        --db_password=\$DB_PASS \
                                        --addons-path=/apps/addons \
                                        -i ${targetModule} --test-enable --stop-after-init --log-level=test --test-tags /${targetModule}
                                    "
                            """
                        }
                    } else {
                        echo "--- SALTANDO TESTS (Mensaje de commit no contiene MOD:nombre_modulo) ---"
                    }
                }
            }
            post {
                always {
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
                                
                                # 1. Forzar variables en archivo .env
                                echo 'POSTGRES_PASSWORD=${TARGET_DB_PASS}' > .env
                                echo 'ODOO_PORT=${ODOO_PORT}' >> .env
                                echo 'COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}' >> .env
                                
                                # 2. Configurar odoo.conf
                                if [ -f "./config/odoo.conf" ]; then
                                    sed -i 's/^db_password =.*/db_password = ${TARGET_DB_PASS}/' ./config/odoo.conf
                                fi
                                
                                echo "--- Reiniciando servicios en EC2 ---"
                                docker compose down --remove-orphans
                                docker system prune -f 
                                docker compose up -d
                                
                                echo "Esperando estabilidad (30s)..."
                                sleep 30
                                
                                # 3. Validación de estado
                                CONTAINER_ID=\\\$(docker compose ps -q odoo)
                                STATUS=\\\$(docker inspect -f '{{.State.Status}}' \\\$CONTAINER_ID)
                                
                                if [ "\\\$STATUS" != "running" ]; then
                                    echo "CRÍTICO: Odoo falló al iniciar."
                                    docker compose logs --tail=50 odoo
                                    exit 1
                                fi

                                echo "--- Actualizando Base de Datos ---"
                                docker compose exec -T -e PGPASSWORD='${TARGET_DB_PASS}' odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init --no-http
EOF
                        """
                    }
                }
            }
        }
    }

    post {
        success { echo "--- DESPLIEGUE OK: http://${EC2_IP}:${ODOO_PORT} ---" }
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